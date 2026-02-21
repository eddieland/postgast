## Why

postgast lists `split` as a core operation but doesn't expose it yet. Users need a way to split a multi-statement SQL
string into individual statements without fully parsing them — this is a fast, scanner-based operation that avoids the
overhead of building an AST and handles edge cases (comments between statements, nested semicolons in parenthesized
expressions) correctly.

## What Changes

- Add a public `split(sql: str) -> list[str]` function that calls libpg_query's `pg_query_split_with_scanner` and
  returns the individual SQL statement strings
- Fix the `PgQuerySplitResult` C struct binding in `_native.py` — the current `stmts` field is typed as
  `POINTER(POINTER(c_int))` but the actual C struct uses `PgQuerySplitStmt **` where each `PgQuerySplitStmt` has
  `stmt_location` and `stmt_len` int fields
- Add a `PgQuerySplitStmt` ctypes struct to `_native.py`
- Export `split` from the `postgast` package `__init__.py`

## Capabilities

### New Capabilities

- `split`: Public function to split a multi-statement SQL string into individual statements using libpg_query's
  scanner-based splitter

### Modified Capabilities

- `c-struct-bindings`: Fix `PgQuerySplitResult.stmts` field type and add missing `PgQuerySplitStmt` struct

## Impact

- `src/postgast/_native.py` — Add `PgQuerySplitStmt` struct, fix `PgQuerySplitResult.stmts` type
- `src/postgast/_split.py` — New module implementing `split()`
- `src/postgast/__init__.py` — Re-export `split`
- `tests/` — New unit tests for `split`
