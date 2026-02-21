## 1. Create conftest.py with fixtures and helpers

- [ ] 1.1 Create `tests/postgast/conftest.py` with parse-result fixtures: `select1_tree`, `create_table_tree`,
  `multi_stmt_tree`, `users_tree`
- [ ] 1.2 Add `assert_roundtrip(sql)` helper to conftest (move from `test_roundtrip.py`)
- [ ] 1.3 Add `assert_pg_query_error(fn, sql, *, check_cursorpos=False)` helper to conftest
- [ ] 1.4 Add parametrized `test_public_api_importable` test over `postgast.__all__` to conftest

## 2. Refactor test files to use fixtures

- [ ] 2.1 Update `test_walk.py`: use `select1_tree` fixture, remove `TestWalkPublicImport`
- [ ] 2.2 Update `test_parse.py`: use `select1_tree`, `create_table_tree`, `multi_stmt_tree` fixtures, use
  `assert_pg_query_error`, remove `TestParsePublicImport`
- [ ] 2.3 Update `test_deparse.py`: use `select1_tree`, `create_table_tree`, `multi_stmt_tree` fixtures, remove
  `TestDeparsePublicImport`
- [ ] 2.4 Update `test_helpers.py`: use `users_tree` fixture, remove `TestOrReplacePublicImport` and
  `TestHelpersPublicImport`
- [ ] 2.5 Update `test_roundtrip.py`: import `assert_roundtrip` from conftest, remove local definition
- [ ] 2.6 Update `test_normalize.py`: use `assert_pg_query_error`, remove `TestPublicImport`
- [ ] 2.7 Update `test_fingerprint.py`: use `assert_pg_query_error`, remove `TestPublicImport`
- [ ] 2.8 Update `test_scan.py`: use `assert_pg_query_error`, remove `TestScanPublicImport`
- [ ] 2.9 Update `test_split.py`: use `assert_pg_query_error`, remove `TestPublicImport`

## 3. Verify

- [ ] 3.1 Run full test suite (`make test`) — all tests pass
- [ ] 3.2 Run `make lint` — no type or lint errors
- [ ] 3.3 Confirm no `TestPublicImport` or `Test*PublicImport` classes remain in any test file
