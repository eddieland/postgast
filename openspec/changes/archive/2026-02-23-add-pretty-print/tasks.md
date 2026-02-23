## 1. Module Scaffold and Infrastructure

- [x] 1.1 Create `src/postgast/format.py` with the `SqlFormatter(Visitor)` class skeleton: `_emit()`, `_newline()`,
  `_indent()`, `_dedent()` helpers, `_parts: list[str]` accumulator, and `_depth: int` indentation tracker
- [x] 1.2 Implement the `format_sql(sql: str | ParseResult) -> str` public function that parses input if needed,
  iterates over `ParseResult.stmts`, formats each via the visitor, joins with semicolons and blank lines, and returns
  the final string
- [x] 1.3 Implement the deparse fallback in `generic_visit` — when no specific `visit_*` handler exists for a statement,
  wrap it in a minimal `ParseResult` and call `deparse()` to produce correct but unformatted SQL
- [x] 1.4 Add `format_sql` to `src/postgast/__init__.py` imports and `__all__`

## 2. Expression Formatting

- [x] 2.1 Implement `visit_A_Const` (integer, float, string, boolean, bit string, null literals)
- [x] 2.2 Implement `visit_ColumnRef` (simple names, qualified names like `schema.table.column`, and `*`)
- [x] 2.3 Implement `visit_A_Expr` (binary operators: `=`, `<>`, `<`, `>`, `+`, `-`, `*`, `/`, `LIKE`, `BETWEEN`, `IN`
  with value list, `IS NULL`/`IS NOT NULL`, unary operators)
- [x] 2.4 Implement `visit_BoolExpr` (AND, OR, NOT — emit AND/OR-separated operands on separate lines when in a WHERE
  context, inline otherwise)
- [x] 2.5 Implement `visit_FuncCall` (function name, arguments, `DISTINCT` in aggregates, star arg for `count(*)`,
  window OVER clause reference)
- [x] 2.6 Implement `visit_TypeCast` and `visit_TypeName` (explicit casts like `CAST(x AS int)` and `::` shorthand)
- [x] 2.7 Implement `visit_CaseExpr` (CASE/WHEN/THEN/ELSE/END with each branch on its own line)
- [x] 2.8 Implement `visit_SubLink` (EXISTS, IN, ANY/ALL, scalar subqueries — emit the inner SELECT indented within
  parentheses)
- [x] 2.9 Implement `visit_NullTest`, `visit_BooleanTest`, `visit_CoalesceExpr`, `visit_MinMaxExpr`, `visit_ParamRef`,
  and other common expression nodes
- [x] 2.10 Test expression formatting: literals, column refs, operators, function calls, CASE, casts, sublinks — verify
  round-trip equivalence for each

## 3. SELECT Statement Formatting

- [x] 3.1 Implement `visit_SelectStmt` core: emit SELECT keyword (with DISTINCT if present), format target list (one
  item per line when multiple via `visit_ResTarget`), handle `SELECT *`
- [x] 3.2 Implement FROM clause formatting: emit FROM keyword, format table references (`visit_RangeVar` with schema,
  alias, and `visit_RangeSubselect` for subqueries in FROM)
- [x] 3.3 Implement JOIN formatting within FROM: `visit_JoinExpr` for INNER/LEFT/RIGHT/FULL/CROSS joins with ON
  condition, multiple JOINs at the same indentation level
- [x] 3.4 Implement WHERE clause formatting: emit WHERE keyword, format the condition expression with AND/OR operands on
  separate indented lines
- [x] 3.5 Implement GROUP BY and HAVING: emit keywords, format group items one per line, format HAVING condition
- [x] 3.6 Implement ORDER BY: emit keyword, format `visit_SortBy` items (expression + ASC/DESC + NULLS FIRST/LAST) one
  per line
- [x] 3.7 Implement LIMIT and OFFSET: emit keywords with their expressions
- [x] 3.8 Test SELECT formatting: simple select, multi-column, joins, WHERE with AND/OR, GROUP BY/HAVING, ORDER BY,
  LIMIT/OFFSET, subqueries in FROM — verify round-trip and idempotency

## 4. CTE and Set Operations

- [x] 4.1 Implement WITH clause formatting: `visit_WithClause` and `visit_CommonTableExpr` — emit WITH keyword, CTE name
  AS (indented body), comma-separated multiple CTEs, RECURSIVE support
- [x] 4.2 Implement set operations in `visit_SelectStmt`: detect `op` field for UNION/INTERSECT/EXCEPT (with ALL), emit
  each branch with the set keyword on its own line between them
- [x] 4.3 Test CTEs and set operations: single CTE, multiple CTEs, UNION, UNION ALL, INTERSECT, EXCEPT — verify
  round-trip

## 5. DML Statement Formatting

- [x] 5.1 Implement `visit_InsertStmt`: INSERT INTO table (columns), VALUES rows or SELECT subquery, ON CONFLICT clause,
  RETURNING clause
- [x] 5.2 Implement `visit_UpdateStmt`: UPDATE table SET assignments (one per line), FROM clause, WHERE clause,
  RETURNING clause
- [x] 5.3 Implement `visit_DeleteStmt`: DELETE FROM table, USING clause, WHERE clause, RETURNING clause
- [x] 5.4 Test DML formatting: INSERT with VALUES, INSERT from SELECT, UPDATE with SET/WHERE, DELETE with WHERE,
  RETURNING clauses — verify round-trip

## 6. DDL Statement Formatting

- [x] 6.1 Implement `visit_CreateStmt`: CREATE TABLE with column definitions and constraints on separate indented lines,
  IF NOT EXISTS, INHERITS, table constraints
- [x] 6.2 Implement `visit_IndexStmt`: CREATE INDEX with table, columns, WHERE clause, UNIQUE, CONCURRENTLY
- [x] 6.3 Implement `visit_ViewStmt`: CREATE VIEW AS select, with OR REPLACE
- [x] 6.4 Implement `visit_AlterTableStmt`: ALTER TABLE with actions (ADD/DROP/ALTER COLUMN, ADD CONSTRAINT)
- [x] 6.5 Implement `visit_DropStmt`: DROP TABLE/INDEX/VIEW with IF EXISTS, CASCADE/RESTRICT
- [x] 6.6 Test DDL formatting: CREATE TABLE, CREATE INDEX, CREATE VIEW, ALTER TABLE, DROP — verify round-trip

## 7. Multi-Statement and Final Integration

- [x] 7.1 Implement multi-statement handling: each statement ends with `;`, separated by blank lines, handle both single
  and multiple statements
- [x] 7.2 Add comprehensive round-trip equivalence tests covering all statement types (parametrize with a list of SQL
  strings)
- [x] 7.3 Add idempotency tests: `format_sql(format_sql(sql)) == format_sql(sql)` for all test cases
- [x] 7.4 Add error handling test: `format_sql()` with invalid SQL raises `PgQueryError`
- [x] 7.5 Add fallback tests: unhandled statement types produce correct SQL via deparse, mixed handled/unhandled
  statements
- [x] 7.6 Run `make lint` and fix any type errors or style issues
