## 1. Core Implementation

- [x] 1.1 Create `src/postgast/_scan.py` with `scan(sql: str) -> ScanResult` function following the encode → call →
  check_error → extract protobuf → deserialize → free pattern
- [x] 1.2 Add `scan` to `src/postgast/__init__.py` exports (`__all__` and import)

## 2. Tests

- [x] 2.1 Create `tests/postgast/test_scan.py` with tests for: simple SELECT tokenization, token byte positions, keyword
  classification, operators, string literals, comments, multi-byte UTF-8, and empty string
- [x] 2.2 Add error handling test: unterminated string literal raises `PgQueryError`
- [x] 2.3 Add public import test: `from postgast import scan` resolves and is callable

## 3. Verify

- [x] 3.1 Run `make lint` (ruff + basedpyright) and fix any issues
- [x] 3.2 Run `make test-unit` and confirm all tests pass
