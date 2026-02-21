## 1. Fix ctypes struct bindings

- [x] 1.1 Add `PgQuerySplitStmt` ctypes Structure to `src/postgast/_native.py` with `stmt_location` (`c_int`) and
  `stmt_len` (`c_int`) fields
- [x] 1.2 Update `PgQuerySplitResult.stmts` from `POINTER(POINTER(c_int))` to `POINTER(POINTER(PgQuerySplitStmt))`

## 2. Implement split function

- [x] 2.1 Create `src/postgast/_split.py` with `split(sql: str) -> list[str]` following the `_normalize.py` pattern:
  encode input as UTF-8 bytes, call `pg_query_split_with_scanner`, check error, extract statements by slicing the byte
  string using `stmt_location`/`stmt_len`, decode each slice, free result in `finally`
- [x] 2.2 Export `split` from `src/postgast/__init__.py` and add to `__all__`

## 3. Tests

- [x] 3.1 Add unit tests for `split()` covering: single statement, two statements, empty string, empty semicolons
  skipped, multi-byte UTF-8 characters, and error on invalid SQL
