## 1. Core Implementation

- [ ] 1.1 Create `src/postgast/_deparse.py` with `deparse(tree: ParseResult) -> str` function that serializes the
  protobuf, constructs a `PgQueryProtobuf` C struct, calls `pg_query_deparse_protobuf`, and returns the SQL string. Use
  `try/finally` to ensure `pg_query_free_deparse_result` is always called. Use `check_error` for error detection.
- [ ] 1.2 Add `deparse` to `src/postgast/__init__.py` imports and `__all__` list

## 2. Tests

- [ ] 2.1 Create `tests/test_deparse.py` with unit tests: simple SELECT round-trip, SELECT with WHERE clause, DDL
  (CREATE TABLE), and multi-statement input
- [ ] 2.2 Add error handling test: passing an invalid/malformed protobuf raises `PgQueryError`
- [ ] 2.3 Add test verifying `from postgast import deparse` works

## 3. Validation

- [ ] 3.1 Run `make lint` and fix any type-checking or linting issues
- [ ] 3.2 Run `make test-unit` and verify all tests pass
