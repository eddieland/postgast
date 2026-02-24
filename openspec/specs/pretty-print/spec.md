## ADDED Requirements

### Requirement: Public API function

`format_sql()` SHALL accept a SQL string (`str`) or a `ParseResult` protobuf message and return a formatted SQL string.
When given a `str`, it SHALL call `parse()` internally. When given a `ParseResult`, it SHALL use it directly. The
function SHALL be importable from `postgast` (re-exported via `__init__.py`).

#### Scenario: Format a SQL string

- **WHEN** `format_sql("select id,name from users where active = true")` is called
- **THEN** it returns a formatted string with uppercase keywords, clause-per-line layout, and indented bodies

#### Scenario: Format a ParseResult

- **WHEN** `format_sql(parse("SELECT 1"))` is called with an already-parsed tree
- **THEN** it returns the same formatted output as `format_sql("SELECT 1")`

#### Scenario: Invalid SQL string

- **WHEN** `format_sql("NOT VALID SQL ???")` is called with unparsable input
- **THEN** it raises `PgQueryError` (propagated from `parse()`)

### Requirement: Semantic equivalence

Formatted output SHALL be semantically equivalent to the input. Specifically, parsing the formatted output and deparsing
it MUST produce the same canonical form as parsing and deparsing the original input.

#### Scenario: Round-trip equivalence for SELECT

- **WHEN** any valid SELECT statement is formatted with `format_sql()`
- **THEN** `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: Round-trip equivalence for DML

- **WHEN** any valid INSERT, UPDATE, or DELETE statement is formatted with `format_sql()`
- **THEN** `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: Round-trip equivalence for DDL

- **WHEN** any valid CREATE TABLE, ALTER TABLE, DROP, CREATE INDEX, or CREATE VIEW statement is formatted
- **THEN** `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

### Requirement: Deterministic output

`format_sql()` SHALL be deterministic — the same input MUST always produce the same output. Formatting an
already-formatted string MUST return the identical string (idempotency).

#### Scenario: Idempotent formatting

- **WHEN** `format_sql(format_sql(sql))` is called on any valid SQL
- **THEN** the result equals `format_sql(sql)`

#### Scenario: Deterministic across calls

- **WHEN** `format_sql(sql)` is called twice with the same input
- **THEN** both calls return the identical string

### Requirement: Uppercase keywords

All SQL keywords SHALL be emitted in uppercase. This includes clause keywords (SELECT, FROM, WHERE, JOIN, GROUP BY,
ORDER BY, HAVING, LIMIT, OFFSET, UNION, INTERSECT, EXCEPT), DML keywords (INSERT, INTO, VALUES, UPDATE, SET, DELETE),
DDL keywords (CREATE, ALTER, DROP, TABLE, INDEX, VIEW, COLUMN, ADD, CONSTRAINT), type keywords (INTEGER, TEXT, BOOLEAN,
VARCHAR, etc.), and expression keywords (AND, OR, NOT, IN, EXISTS, BETWEEN, LIKE, IS, NULL, TRUE, FALSE, CASE, WHEN,
THEN, ELSE, END, AS, ON, USING, ALL, DISTINCT, ASC, DESC, NULLS, FIRST, LAST).

#### Scenario: Keywords in SELECT query

- **WHEN** `format_sql("select id from users where active = true order by id asc")` is called
- **THEN** the output contains `SELECT`, `FROM`, `WHERE`, `ORDER BY`, `ASC` (all uppercase)

#### Scenario: Keywords in JOIN

- **WHEN** a query with `left outer join ... on ...` is formatted
- **THEN** the output contains `LEFT OUTER JOIN` and `ON` in uppercase

### Requirement: Clause-per-line layout

Each major clause SHALL start on a new line at the current base indentation level. Major clauses include: SELECT, FROM,
WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET, WINDOW, FOR UPDATE/SHARE, and set operations (UNION, INTERSECT,
EXCEPT). For INSERT: INSERT INTO, VALUES, ON CONFLICT, RETURNING. For UPDATE: UPDATE, SET, WHERE, RETURNING. For DELETE:
DELETE FROM, WHERE, RETURNING.

#### Scenario: SELECT with multiple clauses

- **WHEN**
  `format_sql("SELECT id, name FROM users WHERE active = true GROUP BY dept HAVING count(*) > 1 ORDER BY name LIMIT 10")`
  is called
- **THEN** SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, and LIMIT each start on their own line

#### Scenario: UPDATE with SET and WHERE

- **WHEN** `format_sql("UPDATE users SET name = 'foo', active = false WHERE id = 1 RETURNING id")` is called
- **THEN** UPDATE, SET, WHERE, and RETURNING each start on their own line

### Requirement: Indented clause bodies

Items within a clause body SHALL be indented by 2 spaces relative to the clause keyword. This applies to SELECT list
items, FROM clause tables, SET clause assignments, WHERE conditions (top-level AND/OR operands), GROUP BY items, ORDER
BY items, and column definitions in CREATE TABLE.

#### Scenario: SELECT list indentation

- **WHEN** a SELECT with multiple columns is formatted
- **THEN** each column appears on its own line, indented 2 spaces from the SELECT keyword

#### Scenario: WHERE with AND

- **WHEN** `format_sql("SELECT 1 FROM t WHERE a = 1 AND b = 2 AND c = 3")` is called
- **THEN** each AND-separated condition appears on its own line, indented 2 spaces from WHERE

### Requirement: One item per line in lists

When a SELECT list, GROUP BY list, or ORDER BY list contains multiple items, each item SHALL appear on its own line.
Single-item lists MAY remain on one line with the clause keyword.

#### Scenario: Multi-column SELECT

- **WHEN** `format_sql("SELECT a, b, c FROM t")` is called
- **THEN** each of `a`, `b`, `c` appears on its own line, separated by commas

#### Scenario: Single-column SELECT

- **WHEN** `format_sql("SELECT id FROM t")` is called
- **THEN** the output MAY keep `id` on the same line as SELECT or on the next line (both acceptable)

#### Scenario: Multi-item ORDER BY

- **WHEN** `format_sql("SELECT * FROM t ORDER BY a ASC, b DESC")` is called
- **THEN** `a ASC` and `b DESC` each appear on their own line under ORDER BY

### Requirement: Subquery indentation

Subqueries (in FROM, WHERE EXISTS/IN, or scalar subqueries) SHALL be indented one additional level relative to their
parent context. The opening parenthesis appears before the subquery, and the closing parenthesis aligns with the
subquery's indentation context.

#### Scenario: Subquery in FROM

- **WHEN** `format_sql("SELECT * FROM (SELECT id FROM users) AS sub")` is called
- **THEN** the inner SELECT is indented relative to the outer FROM clause

#### Scenario: Subquery in WHERE EXISTS

- **WHEN** `format_sql("SELECT * FROM t WHERE EXISTS (SELECT 1 FROM other WHERE other.id = t.id)")` is called
- **THEN** the inner SELECT is indented relative to the WHERE clause

### Requirement: Comma placement

Commas SHALL appear at the end of each item (trailing position on the line), not at the beginning of the next item. No
trailing comma after the last item in a list.

#### Scenario: SELECT list commas

- **WHEN** `format_sql("SELECT a, b, c FROM t")` is called
- **THEN** output shows items as `a,` / `b,` / `c` (commas trail the item, no comma after `c`)

### Requirement: Statement termination

Each statement SHALL end with a semicolon. When multiple statements are formatted, they SHALL be separated by a blank
line.

#### Scenario: Single statement

- **WHEN** `format_sql("SELECT 1")` is called
- **THEN** the output ends with `;`

#### Scenario: Multiple statements

- **WHEN** `format_sql("SELECT 1; SELECT 2")` is called
- **THEN** each statement ends with `;` and they are separated by a blank line

### Requirement: JOIN formatting

JOIN clauses SHALL appear in the FROM section, each on its own line. The JOIN keyword (with optional type prefix like
LEFT, RIGHT, INNER, CROSS, FULL OUTER) starts a new line at the FROM body indentation level. The ON condition follows
the JOIN on the same line when short, or on the next line indented when long.

#### Scenario: Simple JOIN

- **WHEN** `format_sql("SELECT * FROM users JOIN orders ON users.id = orders.user_id")` is called
- **THEN** the JOIN appears on its own line under FROM, with ON on the same line

#### Scenario: Multiple JOINs

- **WHEN** a query with multiple JOINs is formatted
- **THEN** each JOIN starts its own line at the same indentation level

### Requirement: Expression formatting

Expressions (arithmetic, comparisons, function calls, CASE/WHEN, CAST, type casts) SHALL be emitted inline. Function
calls SHALL preserve their argument structure. CASE expressions SHALL have WHEN/THEN/ELSE on separate lines with END
aligned to CASE.

#### Scenario: Function call

- **WHEN** `format_sql("SELECT count(*), sum(amount) FROM orders")` is called
- **THEN** function calls appear inline as `count(*)` and `sum(amount)`

#### Scenario: CASE expression

- **WHEN** a query with `CASE WHEN x = 1 THEN 'a' WHEN x = 2 THEN 'b' ELSE 'c' END` is formatted
- **THEN** each WHEN/THEN pair and the ELSE appear on their own lines, indented within the CASE/END block

### Requirement: CREATE TABLE formatting

CREATE TABLE statements SHALL have each column definition and constraint on its own line, indented within the
parenthesized body. The opening parenthesis follows the table name, and the closing parenthesis appears on its own line.

#### Scenario: CREATE TABLE with columns

- **WHEN** `format_sql("CREATE TABLE users (id serial PRIMARY KEY, name text NOT NULL, email text UNIQUE)")` is called
- **THEN** each column definition appears on its own indented line

### Requirement: Fallback for unhandled statement types

When the formatter encounters a statement type without a specific formatting handler, it SHALL fall back to `deparse()`
to produce correct but unformatted SQL for that statement. The formatter SHALL NOT raise an error for any valid SQL.

#### Scenario: Uncommon statement type

- **WHEN** `format_sql()` is called with a valid SQL statement that has no specific formatter (e.g., `LISTEN channel`)
- **THEN** it returns correct SQL (via deparse fallback) without raising an error

#### Scenario: Mixed handled and unhandled statements

- **WHEN** `format_sql("SELECT 1; LISTEN channel")` is called
- **THEN** the SELECT is pretty-printed and the LISTEN is deparsed correctly, both separated by a blank line

### Requirement: Common DML formatting

INSERT, UPDATE, and DELETE statements SHALL be formatted with clause-per-line layout. INSERT INTO shows the table and
optional column list, followed by VALUES or a subquery. UPDATE shows SET assignments one per line. DELETE FROM shows the
table with optional WHERE clause.

#### Scenario: INSERT with VALUES

- **WHEN** `format_sql("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")` is called
- **THEN** INSERT INTO and VALUES appear on separate lines with proper indentation

#### Scenario: INSERT from SELECT

- **WHEN** `format_sql("INSERT INTO archive SELECT * FROM users WHERE active = false")` is called
- **THEN** INSERT INTO is followed by the SELECT subquery formatted with standard rules

#### Scenario: DELETE with WHERE

- **WHEN** `format_sql("DELETE FROM users WHERE created_at < '2020-01-01'")` is called
- **THEN** DELETE FROM and WHERE appear on separate lines

### Requirement: WITH (CTE) formatting

WITH clauses SHALL appear before the main statement. Each CTE SHALL have its name and AS keyword on one line, followed
by the CTE body indented within parentheses. Multiple CTEs SHALL be separated with commas.

#### Scenario: Single CTE

- **WHEN** `format_sql("WITH active_users AS (SELECT * FROM users WHERE active = true) SELECT * FROM active_users")` is
  called
- **THEN** WITH and the CTE name appear on one line, the CTE body is indented, and the main SELECT follows

#### Scenario: Multiple CTEs

- **WHEN** a query with multiple CTEs is formatted
- **THEN** each CTE is separated by a comma and properly indented

### Requirement: Set operations formatting

UNION, INTERSECT, and EXCEPT (with optional ALL) SHALL appear on their own line between the component SELECT statements,
at the same indentation level as the SELECTs.

#### Scenario: UNION ALL

- **WHEN** `format_sql("SELECT id FROM users UNION ALL SELECT id FROM admins")` is called
- **THEN** UNION ALL appears on its own line between the two SELECT statements

### Requirement: Boolean expression parenthesization

Nested `BoolExpr` nodes SHALL be wrapped in parentheses when the child operator has lower precedence than the parent
operator. SQL operator precedence is: NOT > AND > OR. Specifically:

- An OR child inside an AND parent MUST be parenthesized.
- An AND or OR child inside a NOT parent MUST be parenthesized.
- An AND child inside an OR parent MUST NOT be parenthesized (AND already binds tighter).

This applies in both inline expression contexts and clause-per-line contexts (WHERE, HAVING).

#### Scenario: OR nested inside AND

- **WHEN** `format_sql("SELECT * FROM t WHERE (a = 1 OR b = 2) AND (c = 3 OR d = 4)")` is called
- **THEN** `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`, and the output contains parentheses around
  each OR group

#### Scenario: AND nested inside OR preserves semantics

- **WHEN** `format_sql("SELECT * FROM t WHERE a = 1 OR (b = 2 AND c = 3)")` is called
- **THEN** `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: NOT with compound child

- **WHEN** `format_sql("SELECT * FROM t WHERE NOT (a = 1 AND b = 2)")` is called
- **THEN** `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`, and the output contains
  `NOT (a = 1 AND b = 2)`

#### Scenario: Flat AND does not over-parenthesize

- **WHEN** `format_sql("SELECT * FROM t WHERE a = 1 AND b = 2 AND c = 3")` is called
- **THEN** the output contains no parentheses around the AND operands

### Requirement: Identifier quoting

Identifiers that are PostgreSQL reserved words, contain uppercase letters, start with a digit, or contain characters
other than lowercase ASCII letters, digits, and underscores SHALL be emitted with double-quote delimiters. Identifiers
that do not require quoting SHALL be emitted bare. This applies to column references, table names, schema names, and
alias names.

#### Scenario: Reserved word as column name

- **WHEN** `format_sql('SELECT "order" FROM t')` is called
- **THEN** the output contains `"order"` (quoted) and the formatted SQL parses successfully

#### Scenario: Reserved word as table name

- **WHEN** `format_sql('SELECT * FROM "user"')` is called
- **THEN** the output contains `"user"` (quoted) and `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: Mixed-case identifier

- **WHEN** `format_sql('SELECT "MyColumn" FROM t')` is called
- **THEN** the output contains `"MyColumn"` (quoted, preserving case)

#### Scenario: Plain identifier not quoted

- **WHEN** `format_sql("SELECT name FROM users")` is called
- **THEN** the output contains bare `name` and `users` without double quotes

### Requirement: Window frame clause rendering

Window definitions with non-default frame clauses SHALL render the full frame specification. The frame mode (ROWS,
RANGE, or GROUPS), bounds (UNBOUNDED PRECEDING, CURRENT ROW, N PRECEDING, N FOLLOWING, UNBOUNDED FOLLOWING), and
optional EXCLUDE clause SHALL all be emitted. Default frames (implicit RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT
ROW) SHALL be omitted.

#### Scenario: ROWS BETWEEN with offsets

- **WHEN** `format_sql("SELECT sum(x) OVER (ORDER BY y ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM t")` is called
- **THEN** the output contains `ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING` and `deparse(parse(format_sql(sql)))` equals
  `deparse(parse(sql))`

#### Scenario: RANGE BETWEEN UNBOUNDED

- **WHEN**
  `format_sql("SELECT sum(x) OVER (ORDER BY y RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) FROM t")` is
  called
- **THEN** the output contains `RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`

#### Scenario: GROUPS frame mode

- **WHEN** `format_sql("SELECT sum(x) OVER (ORDER BY y GROUPS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM t")` is called
- **THEN** the output contains `GROUPS BETWEEN 1 PRECEDING AND 1 FOLLOWING`

#### Scenario: Default frame omitted

- **WHEN** `format_sql("SELECT sum(x) OVER (ORDER BY y) FROM t")` is called
- **THEN** the output does NOT contain ROWS, RANGE, GROUPS, PRECEDING, FOLLOWING, or CURRENT ROW

#### Scenario: Frame without BETWEEN

- **WHEN** `format_sql("SELECT sum(x) OVER (ORDER BY y ROWS UNBOUNDED PRECEDING) FROM t")` is called
- **THEN** the output contains `ROWS UNBOUNDED PRECEDING` (no BETWEEN keyword)

### Requirement: DISTINCT ON formatting

`SELECT DISTINCT ON (expr, ...)` SHALL emit the full `DISTINCT ON (...)` clause with the expression list. Bare
`SELECT DISTINCT` (without ON) SHALL continue to emit `DISTINCT` only.

#### Scenario: DISTINCT ON with expression

- **WHEN** `format_sql("SELECT DISTINCT ON (a) a, b FROM t ORDER BY a, b")` is called
- **THEN** the output contains `SELECT DISTINCT ON (a)` and `deparse(parse(format_sql(sql)))` equals
  `deparse(parse(sql))`

#### Scenario: DISTINCT ON with multiple expressions

- **WHEN** `format_sql("SELECT DISTINCT ON (a, b) a, b, c FROM t ORDER BY a, b")` is called
- **THEN** the output contains `SELECT DISTINCT ON (a, b)`

#### Scenario: Bare DISTINCT unchanged

- **WHEN** `format_sql("SELECT DISTINCT a, b FROM t")` is called
- **THEN** the output contains `SELECT DISTINCT` without `ON`

### Requirement: Locking clause rendering

`FOR UPDATE`, `FOR SHARE`, `FOR NO KEY UPDATE`, and `FOR KEY SHARE` clauses SHALL be rendered directly from the
`LockingClause` protobuf fields. The formatter SHALL NOT attempt to deparse `LockingClause` as a standalone statement.
Optional `OF table, ...`, `NOWAIT`, and `SKIP LOCKED` modifiers SHALL be included when present.

#### Scenario: FOR UPDATE

- **WHEN** `format_sql("SELECT * FROM t WHERE id = 1 FOR UPDATE")` is called
- **THEN** the output contains `FOR UPDATE` and `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: FOR SHARE with SKIP LOCKED

- **WHEN** `format_sql("SELECT * FROM t FOR SHARE SKIP LOCKED")` is called
- **THEN** the output contains `FOR SHARE SKIP LOCKED`

#### Scenario: FOR UPDATE OF table NOWAIT

- **WHEN** `format_sql("SELECT * FROM t1, t2 FOR UPDATE OF t1 NOWAIT")` is called
- **THEN** the output contains `FOR UPDATE OF t1 NOWAIT`

#### Scenario: FOR NO KEY UPDATE

- **WHEN** `format_sql("SELECT * FROM t FOR NO KEY UPDATE")` is called
- **THEN** the output contains `FOR NO KEY UPDATE`

### Requirement: Grouping set rendering

`ROLLUP(...)`, `CUBE(...)`, and `GROUPING SETS(...)` in GROUP BY clauses SHALL be rendered with the correct wrapping
keyword and parenthesized content lists. Empty grouping sets SHALL render as `()`.

#### Scenario: ROLLUP

- **WHEN** `format_sql("SELECT a, b, count(*) FROM t GROUP BY ROLLUP (a, b)")` is called
- **THEN** the output contains `ROLLUP(a, b)` and `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: CUBE

- **WHEN** `format_sql("SELECT a, b, count(*) FROM t GROUP BY CUBE (a, b)")` is called
- **THEN** the output contains `CUBE(a, b)`

#### Scenario: GROUPING SETS with empty set

- **WHEN** `format_sql("SELECT a, count(*) FROM t GROUP BY GROUPING SETS ((a), ())")` is called
- **THEN** the output contains `GROUPING SETS` with `(a)` and `()` as members

### Requirement: TABLESAMPLE rendering

`FROM <table> TABLESAMPLE <method>(<args>)` SHALL be rendered with the sampling method and arguments. The optional
`REPEATABLE(<seed>)` clause SHALL be included when present.

#### Scenario: TABLESAMPLE BERNOULLI

- **WHEN** `format_sql("SELECT * FROM t TABLESAMPLE BERNOULLI(10)")` is called
- **THEN** the output contains `t TABLESAMPLE bernoulli(10)` and `deparse(parse(format_sql(sql)))` equals
  `deparse(parse(sql))`

#### Scenario: TABLESAMPLE with REPEATABLE

- **WHEN** `format_sql("SELECT * FROM t TABLESAMPLE SYSTEM(50) REPEATABLE(42)")` is called
- **THEN** the output contains `TABLESAMPLE` with `REPEATABLE(42)`

### Requirement: ROW constructor rendering

`ROW(args...)` constructors SHALL be rendered with the `ROW` keyword when explicitly used and as a parenthesized list
when implicit. The formatter SHALL NOT concatenate arguments without delimiters.

#### Scenario: Explicit ROW constructor

- **WHEN** `format_sql("SELECT ROW(1, 2, 3)")` is called
- **THEN** the output contains `ROW(1, 2, 3)` and `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: Implicit row constructor

- **WHEN** `format_sql("SELECT (1, 2, 3)")` is called
- **THEN** the output contains `(1, 2, 3)` with proper comma separation

### Requirement: Subquery column aliases

When a subquery in FROM or a table function has a column alias list (`AS name(col1, col2, ...)`), the column names SHALL
be emitted after the alias name.

#### Scenario: Subquery with column aliases

- **WHEN** `format_sql("SELECT * FROM (VALUES (1, 2), (3, 4)) AS t(a, b)")` is called
- **THEN** the output contains `AS t(a, b)` and `deparse(parse(format_sql(sql)))` equals `deparse(parse(sql))`

#### Scenario: Subquery with alias but no column names

- **WHEN** `format_sql("SELECT * FROM (SELECT 1) AS sub")` is called
- **THEN** the output contains `AS sub` without column names

### Requirement: Function name pg_catalog prefix stripping

Function names with a `pg_catalog` schema prefix SHALL have that prefix stripped in output, matching the existing
behavior for type names. This avoids exposing internal PostgreSQL catalog names in formatted SQL.

#### Scenario: pg_catalog prefix removed

- **WHEN** `format_sql("SELECT pg_catalog.btrim(name) FROM t")` is called
- **THEN** the output contains `btrim(name)` without the `pg_catalog.` prefix

#### Scenario: Non-pg_catalog schema preserved

- **WHEN** `format_sql("SELECT myschema.myfunc(1)")` is called
- **THEN** the output contains `myschema.myfunc(1)` with the schema prefix intact
