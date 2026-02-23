## ADDED Requirements

### Requirement: Recipe smoke tests

`tests/postgast/test_recipes.py` SHALL contain a parametrized test that executes each recipebook's `marimo.App` via
`app.run()`. The test validates that all cells run without error.

#### Scenario: Each recipe runs without error

- **GIVEN** a recipe module with a `marimo.App` instance named `app`
- **WHEN** `app.run()` is called
- **THEN** it completes without raising an exception

#### Scenario: All three recipes are tested

- **WHEN** the test is collected by pytest
- **THEN** it is parametrized over `recipes.ast_walker`, `recipes.batch_processing`, and `recipes.sql_transforms`

### Requirement: Graceful skip without marimo

The test file SHALL skip gracefully when marimo is not installed, so that `make test` works without the `recipes` extra.

#### Scenario: Tests skip without marimo

- **GIVEN** marimo is not installed in the environment
- **WHEN** `pytest tests/postgast/test_recipes.py` is run
- **THEN** all tests in the file are skipped (not failed)

### Requirement: CI runs recipe tests

The CI test job SHALL install the `recipes` extra so that recipe smoke tests execute on every push.

#### Scenario: CI installs recipes extra

- **WHEN** the CI test job runs
- **THEN** the `recipes` optional extra is installed alongside dev dependencies
