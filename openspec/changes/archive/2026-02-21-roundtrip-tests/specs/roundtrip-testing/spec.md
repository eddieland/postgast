## ADDED Requirements

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
