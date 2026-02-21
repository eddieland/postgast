## Context

`helpers.py` already provides `extract_tables`, `extract_columns`, and `extract_functions` — all taking a parsed
`Message` tree and returning `list[str]` with dot-joined names. The new identity extraction helpers solve a different
problem: returning **separated parts** (schema, name, table) so callers can match against catalog columns directly
without splitting strings. They also target DDL statements (`CreateFunctionStmt`, `CreateTrigStmt`) rather than DML
query nodes.

The AST represents names in two patterns:

- **Repeated Node list** — `CreateFunctionStmt.funcname` is `[String("schema"), String("name")]` or just
  `[String("name")]`.
- **RangeVar struct** — `CreateTrigStmt.relation` has separate `schemaname` and `relname` fields. Trigger name is a
  plain `trigname` string field.

## Goals / Non-Goals

**Goals:**

- Provide `extract_function_identity` and `extract_trigger_identity` that return structured NamedTuples
- Use `None` for absent schema (not empty string) to be idiomatic Python
- Return a singular result (`T | None`) rather than a list, since callers pass single-statement DDL
- Skip procedures in `extract_function_identity` (same AST node, different semantic)

**Non-Goals:**

- View, table, index, sequence, type, or aggregate identity extraction (deferred to future changes)
- A generic `extract_identity()` dispatch function
- Accepting raw SQL strings (callers use `postgast.parse()` first, consistent with existing helpers)

## Decisions

### 1. NamedTuple return types over plain tuples

**Choice**: `FunctionIdentity(schema, name)` and `TriggerIdentity(trigger, schema, table)` as `typing.NamedTuple`
subclasses.

**Why**: The positional meaning differs between types — position 0 is "schema" for functions but "trigger name" for
triggers. NamedTuples are self-documenting (`identity.schema`) while still supporting tuple unpacking. Zero runtime
overhead compared to plain tuples.

**Alternatives considered**:

- Plain tuples — ambiguous positional semantics across types
- Dataclasses — heavier, not unpackable, no benefit here

### 2. `None` for absent schema, not empty string

**Choice**: `schema: str | None` where `None` means unqualified.

**Why**: More idiomatic Python for "not provided." The protobuf uses empty string internally, but `None` better
represents absence at the API boundary. Callers can write `if identity.schema:` either way.

### 3. Singular return (`T | None`) over list

**Choice**: Return the first match or `None`, not a list.

**Why**: These helpers target single-statement DDL. Callers always have one `CREATE FUNCTION` per parse. Multi-statement
input is handled by `postgast.split()` first, then extracting from each. A list return would just mean `result[0]`
everywhere.

If the tree contains multiple matching nodes, only the first (depth-first) is returned. This matches the expected
single-statement usage.

### 4. Procedures silently skipped, not errored

**Choice**: `extract_function_identity` returns `None` when the tree contains only `CreateFunctionStmt` with
`is_procedure=True`.

**Why**: Consistent with returning `None` for "no match" — a procedure is simply not a function. No special error for
this case. A future `extract_procedure_identity` can reuse the same AST traversal with the opposite filter.

### 5. Same module, same patterns

**Choice**: Add both functions and NamedTuples to `helpers.py`, export from `__init__.py`.

**Why**: Follows the established pattern. All helpers live in one module, all are re-exported. The NamedTuples are
defined at module level alongside the functions that return them.

The name extraction logic for `CreateFunctionStmt.funcname` (repeated Node list → sval parts) is nearly identical to
what `extract_functions` already does for `FuncCall.funcname`. Keep it inline rather than extracting a shared helper —
the duplication is minimal and the contexts differ (one returns a list of joined strings, the other returns a
NamedTuple).

## Risks / Trade-offs

**NamedTuples in public API** — Adding `FunctionIdentity` and `TriggerIdentity` to exports increases the API surface. →
Acceptable: they're lightweight, stable types that directly support the function signatures.

**First-match-only semantics** — If someone passes a multi-statement tree, they only get the first identity. → Mitigated
by documentation. The `split()` → extract pattern handles multi-statement input. This matches how callers actually use
DDL extraction (one statement at a time).
