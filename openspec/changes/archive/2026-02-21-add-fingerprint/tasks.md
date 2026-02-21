## 1. Core Implementation

- [x] 1.1 Create `src/postgast/_fingerprint.py` with `FingerprintResult` named tuple and `fingerprint()` function
- [x] 1.2 Add `fingerprint` and `FingerprintResult` to `src/postgast/__init__.py` exports and `__all__`

## 2. Tests

- [x] 2.1 Create `tests/postgast/test_fingerprint.py` with tests for: simple fingerprint, equivalent queries match,
  different queries differ, invalid SQL raises `PgQueryError`
- [x] 2.2 Add tests for `FingerprintResult` named tuple unpacking and field access
- [x] 2.3 Add test for public import (`from postgast import fingerprint, FingerprintResult`)

## 3. Validation

- [x] 3.1 Run `make lint` and fix any type-check or formatting issues
- [x] 3.2 Run `make test-unit` and verify all tests pass
