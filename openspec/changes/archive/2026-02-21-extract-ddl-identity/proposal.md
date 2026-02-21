## Why

Callers who match user-provided DDL against catalog entries (e.g., `pg_proc`, `pg_trigger`) currently rely on fragile
regex to extract schema, name, and table from `CREATE FUNCTION` and `CREATE TRIGGER` statements. These regexes break on
comments before the name, unusual whitespace, `OR REPLACE`, and quoted identifiers. postgast already parses these
statements into a full AST — it should expose helpers that return the identity parts directly.

## What Changes

- Add `extract_function_identity(tree)` — returns a `FunctionIdentity` NamedTuple (`schema: str | None`, `name: str`)
  from a `CreateFunctionStmt` node. Returns `None` if no function is found. Ignores procedures (`is_procedure=True`).
- Add `extract_trigger_identity(tree)` — returns a `TriggerIdentity` NamedTuple (`trigger: str`, `schema: str | None`,
  `table: str`) from a `CreateTrigStmt` node. Returns `None` if no trigger is found.
- Add `FunctionIdentity` and `TriggerIdentity` NamedTuple types to the public API.

## Capabilities

### New Capabilities

- `ddl-identity-extraction`: Parser-based extraction of identity parts (schema, name, table) from DDL statements,
  starting with `CREATE FUNCTION` and `CREATE TRIGGER`.

### Modified Capabilities

- `ast-helpers`: The new functions follow the same pattern as existing helpers (`extract_tables`, etc.) and will be
  exported alongside them. The spec needs a delta to cover the new functions and their NamedTuple return types.

## Impact

- `src/postgast/helpers.py` — new functions and NamedTuple definitions
- `src/postgast/__init__.py` — re-export new functions and types
- `tests/postgast/test_helpers.py` — new test cases
