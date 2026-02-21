## 1. Error Handling

- [x] 1.1 Create `src/postgast/_errors.py` with `PgQueryError` exception class (inherits `Exception`, attributes:
  `message`, `cursorpos`, `context`, `funcname`, `filename`, `lineno`)
- [x] 1.2 Add `_check_error` helper in `_errors.py` that inspects a C result's error pointer, extracts fields, frees the
  result, and raises `PgQueryError` if error is non-null
- [x] 1.3 Add tests for `PgQueryError` construction and `str()` representation
- [x] 1.4 Add tests for `_check_error` with both null and non-null error pointers

## 2. Normalize Function

- [x] 2.1 Create `src/postgast/_normalize.py` with `normalize(query: str) -> str` that calls `pg_query_normalize`, uses
  `_check_error`, extracts the normalized query, and frees the result via try/finally
- [x] 2.2 Add tests for normalization: simple constants, multiple constants, no constants, invalid SQL

## 3. Public API

- [x] 3.1 Update `src/postgast/__init__.py` to re-export `normalize` from `_normalize` and `PgQueryError` from `_errors`
- [x] 3.2 Add test verifying `from postgast import normalize, PgQueryError` works

## 4. Validation

- [x] 4.1 Run `make lint` and fix any type-check or linting issues
- [x] 4.2 Run `make test-unit` and verify all tests pass
