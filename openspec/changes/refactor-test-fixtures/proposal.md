## Why

The test suite has no `conftest.py` and repeats the same SQL strings, parse calls, error assertions, and public-import
checks across many files. Introducing pytest fixtures and shared helpers will reduce boilerplate, make tests easier to
maintain, and establish a pattern for future test development.

## What Changes

- Create `tests/postgast/conftest.py` with shared fixtures and helpers
- Extract common parse results into reusable fixtures (`select1_tree`, `create_table_tree`, `multi_stmt_tree`,
  `users_tree`) to eliminate redundant `parse()` calls across files
- Consolidate the 9 near-identical `TestPublicImport` classes into a single parametrized test
- Extract `assert_roundtrip()` from `test_roundtrip.py` into conftest so `test_deparse.py` can reuse it
- Extract a shared `assert_raises_pg_query_error()` helper to consolidate the 5-file error assertion pattern
- Refactor test files to use the new fixtures and helpers

## Capabilities

### New Capabilities

- `test-fixtures`: Shared pytest fixtures, parametrized helpers, and conftest.py infrastructure for the test suite

### Modified Capabilities

None — this is a pure internal refactoring with no changes to library behavior or spec-level requirements.

## Impact

- `tests/postgast/conftest.py` — new file (fixtures, helpers, parametrized public-import test)
- `tests/postgast/test_parse.py` — use fixtures, remove `TestParsePublicImport`
- `tests/postgast/test_deparse.py` — use fixtures and `assert_roundtrip`, remove `TestDeparsePublicImport`
- `tests/postgast/test_normalize.py` — use error helper, remove `TestPublicImport`
- `tests/postgast/test_fingerprint.py` — use error helper, remove `TestPublicImport`
- `tests/postgast/test_scan.py` — use error helper, remove `TestScanPublicImport`
- `tests/postgast/test_split.py` — use error helper, remove `TestPublicImport`
- `tests/postgast/test_walk.py` — use `select1_tree` fixture, remove `TestWalkPublicImport`
- `tests/postgast/test_helpers.py` — use fixtures, remove `TestOrReplacePublicImport` and `TestHelpersPublicImport`
- `tests/postgast/test_roundtrip.py` — move `assert_roundtrip` to conftest, import from there
- `tests/postgast/test_errors.py` — extract ctypes mock factory into conftest fixture
