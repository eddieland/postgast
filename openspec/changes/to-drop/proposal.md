## Why

Migration tools and schema diff utilities need to produce DROP statements from CREATE definitions. Today this requires
manual string formatting with careful attention to PostgreSQL's identifier quoting, function signature rules, and
per-object-type DROP syntax. Since postgast already has parse and deparse, it can do this correctly via AST surgery —
parse the CREATE, build a DropStmt protobuf, and let libpg_query deparse it.

## What Changes

- Add `to_drop(sql: str) -> str` that accepts a single CREATE FUNCTION, CREATE PROCEDURE, CREATE TRIGGER, or CREATE VIEW
  statement and returns the corresponding DROP statement.
- For functions/procedures, the DROP signature uses types only (no parameter names), matching PostgreSQL's
  `pg_get_function_identity_arguments()` format. OUT and TABLE parameters are excluded.
- Raises `ValueError` on unsupported statement types or multi-statement input.

## Capabilities

### New Capabilities

- `ddl-drop-generation`: Generating DROP statements from CREATE DDL via AST surgery (parse → build DropStmt → deparse).

### Modified Capabilities

- `ast-helpers`: Adding `to_drop` to the set of exported helper functions.

## Impact

- `src/postgast/helpers.py` — new `to_drop()` function
- `src/postgast/__init__.py` — re-export `to_drop`
- `tests/` — new test file for `to_drop`
