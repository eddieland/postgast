## Why

The three recipebook notebooks (`ast_walker.py`, `batch_processing.py`, `sql_transforms.py`) have no automated tests.
They can only be validated by running them interactively with marimo, which means regressions in the recipe logic go
undetected by CI. Since the recipes exercise real postgast APIs (parse, deparse, walk, Visitor, normalize, fingerprint,
split, scan, find_nodes, extract_tables, extract_columns, extract_functions, set_or_replace, ensure_or_replace), testing
them also provides integration-level coverage of the public API in realistic usage patterns.

## What Changes

- Add a test module that imports each recipebook's `marimo.App` and executes all cells programmatically, verifying they
  run without errors and produce expected outputs
- Test the core logic extracted from recipe cells (table extraction, column collection, statement classification,
  subquery detection, complexity measurement, dependency mapping, normalization, fingerprinting, roundtrip, rewriting,
  error handling) with direct assertions — independent of marimo rendering
- Declare `marimo` as available in the test environment so recipe notebooks can be imported (it's already in the
  `recipes` optional extra)

## Capabilities

### New Capabilities

- `recipebook`: Recipebook format, structure, and content requirements (spec already exists — will be modified)
- `testing`: Test suite fixtures, helpers, and coverage requirements (spec already exists — will be modified)

### Modified Capabilities

- `recipebook`: Add requirements for testability — recipe logic must be importable and cells must execute
  programmatically without a marimo server
- `testing`: Add requirements for recipebook test coverage — test files, fixtures, and assertion patterns for recipe
  validation

## Impact

- `tests/postgast/test_recipes.py` — new test file for recipebook validation
- `tests/postgast/conftest.py` — potential new fixtures for recipe testing
- `pyproject.toml` — may need `marimo` added to dev dependencies or test environment
- `recipes/ast_walker.py`, `recipes/batch_processing.py`, `recipes/sql_transforms.py` — no code changes expected, but
  these are the subjects under test
