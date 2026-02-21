## 1. Test Infrastructure

- [x] 1.1 Create `tests/postgast/test_roundtrip.py` with imports (`parse`, `deparse` from `postgast`)
- [x] 1.2 Implement `assert_roundtrip(sql)` helper that verifies canonical stability: `deparse(parse(sql))` produces the
  same string when re-parsed and re-deparsed, with clear error message on failure

## 2. SELECT Roundtrip Tests

- [x] 2.1 Add `test_select_roundtrip` parametrized with simple SELECT cases (column lists, WHERE, ORDER BY, LIMIT,
  DISTINCT, aliases)
- [x] 2.2 Add join cases to SELECT parametrize list (INNER JOIN, LEFT JOIN, RIGHT JOIN, FULL JOIN, CROSS JOIN)
- [x] 2.3 Add subquery cases (subquery in FROM, WHERE EXISTS, WHERE IN (SELECT ...), scalar subquery in SELECT list)
- [x] 2.4 Add CTE cases (single WITH, multiple CTEs, recursive CTE)
- [x] 2.5 Add window function cases (ROW_NUMBER OVER, PARTITION BY, named window)
- [x] 2.6 Add aggregate cases (COUNT, SUM, GROUP BY, HAVING)

## 3. DML Roundtrip Tests

- [x] 3.1 Add `test_dml_roundtrip` parametrized with INSERT cases (VALUES, multi-row VALUES, INSERT ... SELECT, ON
  CONFLICT)
- [x] 3.2 Add UPDATE cases (simple SET, SET from subquery, WHERE, FROM, RETURNING)
- [x] 3.3 Add DELETE cases (simple WHERE, USING, RETURNING)

## 4. DDL Roundtrip Tests

- [x] 4.1 Add `test_ddl_roundtrip` parametrized with CREATE TABLE cases (columns, constraints, defaults, PRIMARY KEY,
  FOREIGN KEY, NOT NULL)
- [x] 4.2 Add ALTER TABLE cases (ADD COLUMN, DROP COLUMN, ADD CONSTRAINT, RENAME)
- [x] 4.3 Add CREATE INDEX cases (simple, unique, expression index)
- [x] 4.4 Add CREATE VIEW and DROP statement cases

## 5. Utility and Edge Case Roundtrip Tests

- [x] 5.1 Add `test_utility_roundtrip` parametrized with EXPLAIN, SET, SHOW, GRANT, REVOKE
- [x] 5.2 Add `test_edge_case_roundtrip` parametrized with quoted identifiers, reserved-word identifiers, mixed-case
  names
- [x] 5.3 Add operator precedence cases (arithmetic grouping, boolean NOT/AND/OR precedence)
- [x] 5.4 Add NULL handling cases (IS NULL, IS NOT NULL, COALESCE, NULLIF)
- [x] 5.5 Add CAST and type expression cases (CAST(... AS ...), `::` shorthand, typed literals)

## 6. Verify

- [x] 6.1 Run `uv run pytest tests/postgast/test_roundtrip.py -v` and confirm all tests pass
- [x] 6.2 Run `make lint` and fix any formatting or type issues
