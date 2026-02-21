## 1. Native bindings

- [x] 1.1 Add `pg_query_split_with_parser` ctypes declaration to `src/postgast/_native.py` with argtypes `[c_char_p]`
  and restype `PgQuerySplitResult`

## 2. Split function

- [x] 2.1 Add `method: Literal["scanner", "parser"] = "parser"` keyword-only parameter to `split()` in
  `src/postgast/_split.py`
- [x] 2.2 Implement dispatch logic: map `"scanner"` → `lib.pg_query_split_with_scanner`, `"parser"` →
  `lib.pg_query_split_with_parser`, raise `ValueError` for anything else
- [x] 2.3 Update docstring to document the `method` parameter

## 3. Tests

- [x] 3.1 Add tests for `method="parser"` covering basic splitting, multi-byte characters, and empty string
- [x] 3.2 Add test that `method="parser"` raises `PgQueryError` on invalid SQL
- [x] 3.3 Add test that an invalid `method` value raises `ValueError`
- [x] 3.4 Verify existing scanner tests still pass (no regressions)
