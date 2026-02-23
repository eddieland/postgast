## Why

The three recipebook notebooks (`ast_walker.py`, `batch_processing.py`, `sql_transforms.py`) exercise real postgast APIs
but have no automated validation. They can only be checked by running them interactively with marimo. When the library's
API changes (renamed functions, changed signatures, removed exports), the recipes silently go stale. Running them in CI
catches this drift automatically.

## What Changes

- Add a test module that imports each recipe's `marimo.App` and calls `app.run()` to execute all cells programmatically
  — any cell that errors fails the test
- Use `pytest.importorskip("marimo")` so the test is skipped gracefully when the `recipes` extra is not installed
- Install the `recipes` extra in the CI test job so recipe tests actually run

## Capabilities

### Modified Capabilities

- `testing`: Add recipe smoke tests that execute recipebook cells via `app.run()`

## Impact

- `tests/postgast/test_recipes.py` — new test file (parametrized over recipe modules)
- `.github/workflows/ci.yml` — install `recipes` extra in test job
- `recipes/ast_walker.py`, `recipes/batch_processing.py`, `recipes/sql_transforms.py` — subjects under test; may need
  bug fixes for tests to pass
