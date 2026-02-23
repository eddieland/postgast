## ADDED Requirements

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
