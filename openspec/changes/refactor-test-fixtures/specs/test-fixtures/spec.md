## ADDED Requirements

### Requirement: Shared parse-result fixtures

`tests/postgast/conftest.py` SHALL provide pytest fixtures that return pre-parsed results for commonly used SQL strings.
Each fixture SHALL have `function` scope (the pytest default) so that tests receive independent protobuf instances.

Fixtures:

- `select1_tree` — `parse("SELECT 1")`
- `create_table_tree` — `parse("CREATE TABLE t (id int PRIMARY KEY, name text)")`
- `multi_stmt_tree` — `parse("SELECT 1; SELECT 2")`
- `users_tree` — `parse("SELECT * FROM users")`

#### Scenario: Fixture returns a fresh parse result per test

- **WHEN** two tests in the same module both request `select1_tree`
- **THEN** each receives an independent `ParseResult` object (not the same instance)

#### Scenario: Fixture result is structurally correct

- **WHEN** a test requests `select1_tree`
- **THEN** the result has `len(result.stmts) == 1` and `result.stmts[0].stmt.HasField("select_stmt")`

### Requirement: Public API import test

`conftest.py` SHALL contain a single parametrized test `test_public_api_importable` that verifies every name in
`postgast.__all__` is importable and resolves to a valid object.

This test SHALL replace all per-module `TestPublicImport` / `TestXxxPublicImport` classes. Those classes SHALL be
removed from their respective test files.

#### Scenario: All public API names are importable

- **WHEN** the parametrized test runs over `postgast.__all__`
- **THEN** `getattr(postgast, name)` succeeds for every entry

#### Scenario: Functions are callable

- **WHEN** the entry is a function (e.g., `parse`, `deparse`, `normalize`)
- **THEN** `callable(getattr(postgast, name))` is `True`

#### Scenario: Removed boilerplate classes

- **WHEN** the refactoring is complete
- **THEN** no test file in `tests/postgast/` contains a class whose name matches `Test*PublicImport`

### Requirement: Shared roundtrip assertion helper

`conftest.py` SHALL provide an `assert_roundtrip(sql: str)` function that asserts `deparse(parse(sql))` produces a
stable canonical form (deparsing the re-parsed canonical SQL produces the same string).

`test_roundtrip.py` SHALL import `assert_roundtrip` from `conftest` instead of defining it locally.

#### Scenario: Helper is available to any test file

- **WHEN** `test_deparse.py` or any other test file calls `assert_roundtrip("SELECT 1")`
- **THEN** the assertion passes without import errors

#### Scenario: Behavior matches original implementation

- **WHEN** `assert_roundtrip` is called with SQL that has a stable canonical form
- **THEN** it passes, identical to the behavior of the original `test_roundtrip.py` implementation

### Requirement: Shared error assertion helper

`conftest.py` SHALL provide an `assert_pg_query_error(fn, sql, *, check_cursorpos=False)` helper that:

1. Calls `fn(sql)` inside `pytest.raises(PgQueryError)`
1. Asserts `exc_info.value.message` is truthy
1. If `check_cursorpos=True`, asserts `exc_info.value.cursorpos > 0`

Test files that currently inline this pattern SHALL use the helper instead.

#### Scenario: Basic error assertion

- **WHEN** `assert_pg_query_error(split, "SELECT '")` is called
- **THEN** it verifies that `PgQueryError` is raised and `.message` is truthy

#### Scenario: Error assertion with cursorpos check

- **WHEN** `assert_pg_query_error(parse, "SELECT FROM", check_cursorpos=True)` is called
- **THEN** it additionally verifies `.cursorpos > 0`

#### Scenario: Replaces inline error patterns

- **WHEN** the refactoring is complete
- **THEN** `test_parse.py`, `test_normalize.py`, `test_fingerprint.py`, `test_split.py`, and `test_scan.py` use the
  shared helper instead of inlining `pytest.raises` + `.message` assertions

### Requirement: Test files use fixtures instead of inline parse calls

Test files that currently call `parse()` with SQL strings matching a fixture's input SHALL use the corresponding fixture
parameter instead. Tests that use unique SQL strings not covered by a fixture SHALL continue calling `parse()` inline.

#### Scenario: test_walk.py uses select1_tree

- **WHEN** tests in `TestWalk` or `TestVisitor` need `parse("SELECT 1")`
- **THEN** they accept `select1_tree` as a fixture parameter instead of calling `parse()` directly

#### Scenario: test_helpers.py uses users_tree

- **WHEN** tests in `TestExtractTables`, `TestExtractColumns`, or `TestHelpersOnSubtree` need
  `parse("SELECT * FROM users")`
- **THEN** they accept `users_tree` as a fixture parameter

#### Scenario: Unique SQL strings remain inline

- **WHEN** a test uses a SQL string not covered by any fixture (e.g., `"SELECT * FROM orders JOIN customers..."`)
- **THEN** it continues calling `parse()` inline — no fixture is created for one-off inputs
