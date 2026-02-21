## 1. Protobuf Bindings

- [x] 1.1 Add `protobuf>=5.29` to `dependencies` in `pyproject.toml` and run `uv sync`
- [x] 1.2 Generate `_pg_query_pb2.py` by running `protoc --python_out` against
  `vendor/libpg_query/protobuf/pg_query.proto` and place it at `src/postgast/_pg_query_pb2.py`
- [x] 1.3 Add `make proto` target to the Makefile for regenerating the protobuf bindings
- [x] 1.4 Verify `from postgast._pg_query_pb2 import ParseResult` works and `ParseResult` has `version` and `stmts`
  fields

## 2. Parse Function

- [x] 2.1 Create `src/postgast/_parse.py` with `parse(query: str) -> ParseResult` following the `_normalize.py` pattern:
  encode to UTF-8, call `lib.pg_query_parse_protobuf`, check error, extract bytes via `ctypes.string_at`, deserialize
  with `ParseResult.FromString`, free result in `finally`
- [x] 2.2 Update `src/postgast/__init__.py` to import and re-export `parse` and `pg_query_pb2` (as a public module alias
  for `_pg_query_pb2`)

## 3. Tests

- [x] 3.1 Add `tests/postgast/test_parse.py` with tests for: simple SELECT, multi-statement, DDL (CREATE TABLE), invalid
  SQL raising `PgQueryError`, empty string returning empty `stmts`, and top-level import (`from postgast import parse`)
- [x] 3.2 Add `tests/postgast/test_protobuf_bindings.py` with tests for: `_pg_query_pb2` importability, `ParseResult`
  message structure, and `from postgast import pg_query_pb2` re-export

## 4. Validation

- [x] 4.1 Run `make lint` (ruff + basedpyright) and fix any issues
- [x] 4.2 Run `make test-unit` and verify all tests pass
