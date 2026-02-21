## Context

The test suite (11 test files in `tests/postgast/`) has no `conftest.py`. Each file independently imports, calls, and
asserts against the same SQL inputs, parse results, and error patterns. As the test surface grows, this repetition makes
tests harder to maintain and obscures what each test is actually verifying.

## Goals / Non-Goals

**Goals:**

- Introduce `tests/postgast/conftest.py` as the single home for shared fixtures and helpers
- Eliminate redundant `parse()` calls by providing pre-parsed fixture results
- Replace 9 boilerplate `TestPublicImport` classes with one parametrized test
- Share the `assert_roundtrip` helper so it's usable from any test file
- Share a `assert_pg_query_error` helper across the 5 files that test error raising
- Keep every existing test passing with identical coverage

**Non-Goals:**

- Restructuring test file organization or renaming test files
- Changing test logic or assertions beyond switching to fixtures/helpers
- Adding new test coverage (this is purely a DRY refactoring)
- Changing fixture scope to `module` or `session` — parse calls are fast (~microseconds) and mutable protobuf objects
  should not be shared across tests

## Decisions

### 1. Fixture scope: `function` (default) for all parse-result fixtures

Parse results are mutable protobuf messages. Sharing a single instance across tests via `module` or `session` scope
would risk one test's mutations affecting another. The parse calls are fast enough that per-test overhead is negligible.

**Alternative considered:** `module` scope with `deepcopy` — adds complexity for no real benefit given parse speed.

### 2. Fixtures as plain functions, not factory fixtures

Each fixture returns a pre-parsed result for a specific SQL string (e.g., `select1_tree` returns `parse("SELECT 1")`).
Tests that need a different SQL string still call `parse()` inline. This keeps fixtures simple and avoids
over-abstraction.

**Alternative considered:** A `parse_fixture` factory that takes SQL as a parameter — too indirect, harder to read, and
most repeated SQL strings are a small fixed set.

### 3. Public-import test: single parametrized test over `__all__`

Replace the 9 `TestPublicImport` classes with a single `test_public_api_importable` function parametrized over the
entries in `postgast.__all__`. This automatically covers new exports without manual test additions.

The test checks `callable()` for functions and `issubclass(..., type)` or `issubclass(..., tuple)` for classes/named
tuples. Since the current tests only assert `callable()` or `issubclass()`, a simple `hasattr(postgast, name)` check
plus type-specific assertions covers the same ground.

**Alternative considered:** Keep separate per-module import tests — more boilerplate, no added value since they all test
the same thing (symbol exists and is importable).

### 4. `assert_roundtrip` stays a plain function, moves to conftest

Currently defined in `test_roundtrip.py` as a module-level function. Moving it to `conftest.py` makes it available to
`test_deparse.py` and any future test file that needs roundtrip verification. It stays a plain function (not a fixture)
because it takes a SQL string argument — it's an assertion helper, not a data provider.

### 5. `assert_pg_query_error`: helper function, not fixture

The error assertion pattern (`pytest.raises(PgQueryError)` + `assert exc_info.value.message`) repeats across 5 files. A
helper function `assert_pg_query_error(fn, sql, *, check_cursorpos=False)` in conftest consolidates this. It stays a
plain function because it needs `fn` and `sql` arguments.

### 6. ctypes mock factory: keep in `test_errors.py`

The `_MockResult` struct and `CPgQueryError` construction in `test_errors.py` is only used in that one file. Moving it
to conftest would pollute the shared namespace with ctypes internals that no other test file needs. A local helper
function within `test_errors.py` is sufficient.

**Alternative considered:** Fixture in conftest — rejected because only one file uses it, and it requires ctypes imports
that are test_errors-specific.

## Risks / Trade-offs

- **Fixture indirection** — Tests that use `select1_tree` instead of `parse("SELECT 1")` are slightly less
  self-contained. Mitigated by using clear fixture names and keeping fixtures simple (one-liner bodies).
- **Parametrized public-import test loses per-module grouping** — The current pattern groups import tests next to the
  feature they test. The parametrized approach moves them to conftest. Acceptable because the tests are trivial
  assertions that don't benefit from proximity to feature tests.
- **`assert_roundtrip` relocation** — `test_roundtrip.py` will import from conftest instead of defining locally. This is
  standard pytest practice and not a real risk.
