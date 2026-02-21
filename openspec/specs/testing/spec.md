# testing Specification

## Purpose

Define shared pytest fixtures, assertion helpers, and roundtrip coverage requirements for the test suite.

## Requirements

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

### Requirement: No boilerplate public import tests

Per-module `TestPublicImport` / `TestXxxPublicImport` classes SHALL NOT exist in any test file. Public API importability
is validated statically by pyright via the type-checked `__init__.py` re-exports.

#### Scenario: No import test classes remain

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

### Requirement: Roundtrip AST equivalence

The test suite SHALL verify that for each supported SQL statement, `parse(deparse(parse(sql)))` produces a `ParseResult`
protobuf identical to `parse(sql)`. This confirms that no semantic information is lost through the parse-deparse cycle.

#### Scenario: Simple SELECT roundtrips

- **WHEN** `"SELECT a, b FROM t WHERE x = 1"` is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: SELECT with joins roundtrips

- **WHEN** a SELECT with JOIN clauses (INNER, LEFT, RIGHT, FULL, CROSS) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: SELECT with subqueries roundtrips

- **WHEN** a SELECT containing subqueries (in FROM, WHERE, or SELECT list) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: SELECT with CTEs roundtrips

- **WHEN** a SELECT using `WITH` common table expressions is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: SELECT with window functions roundtrips

- **WHEN** a SELECT using window functions (`OVER`, `PARTITION BY`, `ORDER BY`) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: SELECT with aggregates and GROUP BY roundtrips

- **WHEN** a SELECT with aggregate functions and `GROUP BY`/`HAVING` is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

### Requirement: DML statement roundtrips

The test suite SHALL verify roundtrip equivalence for INSERT, UPDATE, DELETE, and MERGE statements.

#### Scenario: INSERT roundtrips

- **WHEN** an INSERT statement (with VALUES, or INSERT ... SELECT) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: UPDATE roundtrips

- **WHEN** an UPDATE statement (with SET, WHERE, FROM, and RETURNING) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: DELETE roundtrips

- **WHEN** a DELETE statement (with WHERE, USING, and RETURNING) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

### Requirement: DDL statement roundtrips

The test suite SHALL verify roundtrip equivalence for CREATE, ALTER, and DROP statements across tables, indexes, views,
and types.

#### Scenario: CREATE TABLE roundtrips

- **WHEN** a CREATE TABLE statement (with columns, constraints, and defaults) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: ALTER TABLE roundtrips

- **WHEN** an ALTER TABLE statement (ADD COLUMN, DROP COLUMN, ADD CONSTRAINT) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: CREATE INDEX roundtrips

- **WHEN** a CREATE INDEX statement (including expression indexes) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: CREATE VIEW roundtrips

- **WHEN** a CREATE VIEW statement is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: DROP statement roundtrips

- **WHEN** a DROP TABLE/INDEX/VIEW statement is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

### Requirement: Utility statement roundtrips

The test suite SHALL verify roundtrip equivalence for common utility statements.

#### Scenario: EXPLAIN roundtrips

- **WHEN** an EXPLAIN (or EXPLAIN ANALYZE) statement is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: SET/SHOW roundtrips

- **WHEN** a SET or SHOW statement is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: GRANT/REVOKE roundtrips

- **WHEN** a GRANT or REVOKE statement is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

### Requirement: Edge case roundtrips

The test suite SHALL verify roundtrip equivalence for SQL constructs that stress quoting, precedence, and special
values.

#### Scenario: Quoted identifiers roundtrip

- **WHEN** a statement with double-quoted identifiers (e.g., `"MixedCase"`, `"select"`) is parsed, deparsed, and
  re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: Operator precedence roundtrips

- **WHEN** a statement with complex expressions requiring parentheses for correctness (e.g., `(a + b) * c`,
  `NOT (x AND y)`) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: NULL handling roundtrips

- **WHEN** a statement using `NULL`, `IS NULL`, `IS NOT NULL`, and `COALESCE` is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

#### Scenario: CAST and type expressions roundtrip

- **WHEN** a statement with explicit CAST expressions and typed literals (e.g., `CAST(x AS integer)`,
  `'2024-01-01'::date`) is parsed, deparsed, and re-parsed
- **THEN** the re-parsed `ParseResult` equals the original `ParseResult`

### Requirement: Test organization by SQL category

Test cases SHALL be organized into separate parametrized test methods by SQL category (SELECT, DML, DDL, utility, edge
cases) so that failures clearly identify which syntax area is affected.

#### Scenario: Failure identifies category

- **WHEN** a roundtrip test fails
- **THEN** the test name includes the SQL category (e.g., `test_select_roundtrip`, `test_ddl_roundtrip`) so the failing
  syntax area is immediately apparent from the test output
