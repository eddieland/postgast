## ADDED Requirements

### Requirement: AST walker recipe tests

`tests/postgast/test_recipes.py` SHALL contain a `TestAstWalkerRecipes` class that validates the postgast API patterns
demonstrated in `recipes/ast_walker.py`. Tests SHALL call postgast APIs directly with the same SQL patterns used in the
recipes, without importing the recipe module or requiring marimo.

#### Scenario: Table extraction via Visitor

- **WHEN** a `Visitor` subclass with `visit_RangeVar` is run against a parsed multi-JOIN query
- **THEN** it collects all table names referenced in the query

#### Scenario: Column reference collection via walk

- **WHEN** `walk()` is used to iterate over a parsed SELECT with multiple column references
- **THEN** filtering for `ColumnRef` nodes and extracting `fields[].string.sval` yields all column names

#### Scenario: Statement type classification

- **WHEN** a multi-statement SQL string (SELECT, INSERT, CREATE) is parsed
- **THEN** inspecting `stmt.WhichOneof("node")` on each `RawStmt` returns the correct statement type

#### Scenario: Subquery detection via walk

- **WHEN** `walk()` is used on a query containing nested `SELECT` subqueries
- **THEN** `SelectStmt` nodes beyond the first (top-level) one are identified as subqueries

#### Scenario: Query complexity measurement

- **WHEN** a simple query and a complex multi-join query are each analyzed by counting nodes, `JoinExpr`, and
  `BoolExpr`/`A_Expr`
- **THEN** the complex query produces a higher complexity score

#### Scenario: Schema dependency mapping

- **WHEN** DDL and DML statements are parsed and table names are extracted per statement
- **THEN** INSERT/CREATE statements that reference multiple tables produce dependency edges

#### Scenario: Helper function equivalence

- **WHEN** `extract_tables`, `extract_columns`, `extract_functions`, and `find_nodes` are called on a parsed query
- **THEN** each returns correct results matching what manual Visitor/walk patterns would produce

#### Scenario: Per-statement analysis with helpers

- **WHEN** a multi-statement SQL string is parsed and each statement is analyzed with `extract_tables`,
  `extract_columns`, and `extract_functions`
- **THEN** each statement's metadata (type, tables, columns, functions) is correctly extracted

### Requirement: Batch processing recipe tests

`tests/postgast/test_recipes.py` SHALL contain a `TestBatchProcessingRecipes` class that validates the postgast API
patterns demonstrated in `recipes/batch_processing.py`.

#### Scenario: Split and parse migration

- **WHEN** a multi-statement migration SQL is passed to `split()` and each result is parsed
- **THEN** each statement parses successfully with correct statement type and table references

#### Scenario: SQL tokenization

- **WHEN** `scan()` is called on a SQL string
- **THEN** the result contains tokens with valid `token`, `keyword_kind`, `start`, and `end` fields, and token text
  extracted via byte slicing matches expected values

#### Scenario: Query log deduplication via normalize and fingerprint

- **WHEN** structurally equivalent queries with different literal values are normalized and fingerprinted
- **THEN** `normalize()` produces identical templates and `fingerprint()` produces identical hex values

#### Scenario: Migration dependency graph via foreign keys

- **WHEN** CREATE TABLE statements with REFERENCES constraints are parsed and `find_nodes` is used to locate
  `Constraint` nodes with `pktable`
- **THEN** the foreign key dependencies are correctly extracted

#### Scenario: Comment extraction via scan

- **WHEN** `scan()` is called on SQL containing `--` and `/* */` comments
- **THEN** `SQL_COMMENT` and `C_COMMENT` tokens are identified with correct byte positions

#### Scenario: Batch execution plan with error handling

- **WHEN** a batch of SQL statements (including one with a syntax error) is split, parsed, and classified
- **THEN** valid statements are classified by type and invalid statements raise `PgQueryError` with a truthy message

### Requirement: SQL transforms recipe tests

`tests/postgast/test_recipes.py` SHALL contain a `TestSqlTransformsRecipes` class that validates the postgast API
patterns demonstrated in `recipes/sql_transforms.py`.

#### Scenario: Parse-deparse roundtrip normalization

- **WHEN** cosmetically different SQL variants (extra whitespace, different casing, newlines) are each passed through
  `deparse(parse(sql))`
- **THEN** all variants produce the same canonical output

#### Scenario: Normalize for log analysis

- **WHEN** queries differing only in literal values are passed to `normalize()`
- **THEN** they produce identical parameterized templates with `$N` placeholders

#### Scenario: Fingerprint structural equivalence

- **WHEN** structurally equivalent queries with different literals are fingerprinted
- **THEN** they produce the same fingerprint hex, while structurally different queries produce different hex values

#### Scenario: AST rewriting via find_nodes

- **WHEN** `find_nodes` locates `RangeVar` nodes and their `schemaname` or `relname` fields are modified, then the tree
  is deparsed
- **THEN** the output SQL reflects the modifications (schema prefix added, table renamed)

#### Scenario: ensure_or_replace on eligible DDL

- **WHEN** `set_or_replace` is called on parsed CREATE FUNCTION, CREATE VIEW, and CREATE TRIGGER statements
- **THEN** it returns a count > 0 and deparsing produces SQL with `OR REPLACE`

#### Scenario: ensure_or_replace skips ineligible DDL

- **WHEN** `set_or_replace` is called on a parsed CREATE TABLE statement
- **THEN** it returns 0 and the deparsed output is unchanged

#### Scenario: Structured error inspection

- **WHEN** syntactically invalid SQL is passed to `parse()`
- **THEN** `PgQueryError` is raised with a truthy `message` and (for most errors) a `cursorpos > 0`

### Requirement: Recipe test organization

Recipe tests SHALL be organized into test classes by recipebook (`TestAstWalkerRecipes`, `TestBatchProcessingRecipes`,
`TestSqlTransformsRecipes`) within a single `tests/postgast/test_recipes.py` file. Each test method SHALL be named to
identify the API pattern being tested.

#### Scenario: Test classes match recipebooks

- **WHEN** `test_recipes.py` is examined
- **THEN** it contains exactly three test classes, one per recipebook

#### Scenario: Tests run without marimo

- **WHEN** `uv run pytest tests/postgast/test_recipes.py` is executed without the `recipes` extra installed
- **THEN** all tests pass because they use postgast APIs directly and do not import marimo or recipe modules
