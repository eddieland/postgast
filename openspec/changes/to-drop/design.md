## Context

postgast provides `ensure_or_replace()` as a parse → transform → deparse pipeline in `helpers.py`. The `to_drop()`
function follows the same pattern: parse a CREATE statement, build a `DropStmt` protobuf node from the parsed fields,
wrap it in a `ParseResult`, and deparse it back to SQL.

libpg_query's deparse already handles DROP FUNCTION, DROP PROCEDURE, DROP TRIGGER, and DROP VIEW correctly, including
identifier quoting and type normalization. The three DROP shapes use different protobuf structures:

- **FUNCTION/PROCEDURE**: `DropStmt.objects` contains `ObjectWithArgs` (name + typed parameter list)
- **TRIGGER**: `DropStmt.objects` contains a `List` of `[schema?, table, trigger_name]` strings
- **VIEW**: `DropStmt.objects` contains a `List` of `[schema?, view_name]` strings

## Goals / Non-Goals

**Goals:**

- Produce correct DROP statements for CREATE FUNCTION, CREATE PROCEDURE, CREATE TRIGGER, and CREATE VIEW
- Handle function identity arguments correctly (types only, no names, exclude OUT/TABLE params)
- Handle quoted identifiers, schema qualification, and VARIADIC parameters
- Delegate all SQL formatting to libpg_query's deparse (no string interpolation)

**Non-Goals:**

- IF EXISTS or CASCADE/RESTRICT flags (can be added later with keyword arguments)
- Other DDL types (TABLE, INDEX, SEQUENCE, MATERIALIZED VIEW)
- Batch processing (multi-statement input)
- Accepting pre-parsed `ParseResult` input (only raw SQL string)

## Decisions

### AST surgery over string formatting

Build a `DropStmt` protobuf and deparse it, rather than string-formatting from extracted fields.

- **Why**: libpg_query handles identifier quoting, type normalization (`integer` → `int`), and the three different DROP
  object encodings. String formatting would require reimplementing all of this.
- **Alternative**: Extract identity fields and use f-strings. Rejected because it creates a quoting/escaping surface
  area that libpg_query already solves.

### Function parameter filtering

For DROP FUNCTION/PROCEDURE signatures, include only IN, INOUT, and VARIADIC parameters. Strip parameter names and
default expressions, keeping only `arg_type`.

- **Why**: This matches PostgreSQL's `pg_get_function_identity_arguments()` behavior. OUT and TABLE parameters are not
  part of the function's identity for overload resolution.
- **Detail**: Copy each kept parameter's `arg_type` via `CopyFrom` and set mode to `FUNC_PARAM_DEFAULT` (the mode used
  by parsed DROP statements).

### Single function, not per-type helpers

One `to_drop()` function that dispatches internally, not `function_to_drop()` / `trigger_to_drop()` / `view_to_drop()`.

- **Why**: The user doesn't need to know the statement type — they have a CREATE statement and want a DROP statement.
  Internal dispatch keeps the public API minimal.

### Strict single-statement input

Raise `ValueError` if the input contains zero or more than one statement, or if the statement is not a supported CREATE
type.

- **Why**: Multi-statement input creates ambiguity about what to return (one DROP? many?). Raising keeps the API
  predictable. This matches the principle that `to_drop` is a 1:1 transform.

## Risks / Trade-offs

- **[protobuf construction verbosity]** → Building protobuf nodes by hand is verbose but straightforward. The three
  builder paths are isolated, so complexity is linear not combinatorial.
- **[libpg_query deparse fidelity]** → We depend on libpg_query producing correct DROP SQL. The roundtrip tests already
  validate this for all three DROP types. Minimal risk.
