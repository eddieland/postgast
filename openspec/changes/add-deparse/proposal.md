## Why

postgast can parse SQL into a protobuf AST but cannot convert that AST back into SQL text. Adding `deparse` completes
the parse-modify-deparse round-trip, enabling users to programmatically rewrite SQL queries — a core use case for query
analysis and transformation tools. The C binding (`pg_query_deparse_protobuf`) and result struct
(`PgQueryDeparseResult`) are already declared in `_native.py`, so only the Python wrapper and public API export are
missing.

## What Changes

- Add a `deparse(tree: ParseResult) -> str` function that serializes a `ParseResult` protobuf to bytes, passes it to
  `pg_query_deparse_protobuf`, and returns the resulting SQL string
- Export `deparse` from `postgast.__init__` so it is importable as `from postgast import deparse`
- Add unit tests covering round-trip (parse then deparse), direct deparse of hand-built protobuf trees, and error
  handling

## Capabilities

### New Capabilities

- `deparse`: Convert a protobuf `ParseResult` AST back into a SQL text string via `pg_query_deparse_protobuf`

### Modified Capabilities

_(none — no existing spec requirements change)_

## Impact

- **New file**: `src/postgast/_deparse.py` — deparse implementation (following `_parse.py` / `_normalize.py` pattern)
- **Modified file**: `src/postgast/__init__.py` — add `deparse` to imports and `__all__`
- **New file**: `tests/test_deparse.py` — unit and integration tests
- **C API**: Uses `pg_query_deparse_protobuf` (input: `PgQueryProtobuf` struct) and `pg_query_free_deparse_result`
  (already declared in `_native.py`)
- **Dependencies**: No new dependencies — uses existing `protobuf` and `ctypes` infrastructure
