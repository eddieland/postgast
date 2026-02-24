## ADDED Requirements

### Requirement: Notebook file and format

The recipebook SHALL be a Marimo notebook at `recipes/ast_walker.py` using the `marimo.App()` / `@app.cell` format. The
file SHALL be executable as a standalone script (`python recipes/ast_walker.py`), runnable as an app
(`marimo run recipes/ast_walker.py`), and editable interactively (`marimo edit recipes/ast_walker.py`).

#### Scenario: File exists as valid Marimo notebook

- **WHEN** a user opens `recipes/ast_walker.py`
- **THEN** the file contains a `marimo.App()` instance and one or more `@app.cell` decorated functions

#### Scenario: Runnable as marimo app

- **WHEN** a user runs `marimo run recipes/ast_walker.py`
- **THEN** the notebook opens in a browser and all cells execute without error

### Requirement: Shared imports cell

The notebook SHALL have a cell that imports `postgast` public API symbols (`parse`, `deparse`, `walk`, `Visitor`,
`pg_query_pb2`) and `marimo as mo`. Other recipe cells SHALL declare these as function parameters to receive them via
marimo's reactive dependency system.

#### Scenario: Imports cell provides postgast API

- **WHEN** the notebook loads
- **THEN** the imports cell exports `parse`, `deparse`, `walk`, `Visitor`, `pg_query_pb2`, and `mo` for use by
  downstream cells

### Requirement: Recipe — Extract table names

The notebook SHALL include a recipe demonstrating table name extraction using the `Visitor` pattern. The recipe SHALL
define a `Visitor` subclass with a `visit_RangeVar` method that collects `relname` values, run it against a multi-table
SQL query, and display the collected table names.

#### Scenario: Visitor collects tables from JOIN query

- **WHEN** the recipe cell executes with a SQL query containing multiple JOINed tables
- **THEN** it displays all table names found in the query

### Requirement: Recipe — Collect column references

The notebook SHALL include a recipe demonstrating column reference collection using the `walk()` generator. The recipe
SHALL iterate over `walk()` results, filter for `ColumnRef` message types, extract column name strings from the `fields`
repeated field, and display the collected column names.

#### Scenario: walk() filters ColumnRef nodes

- **WHEN** the recipe cell executes with a SELECT query referencing multiple columns
- **THEN** it displays all column names found in the query

### Requirement: Recipe — Classify statement type

The notebook SHALL include a recipe that classifies SQL statements by their top-level AST node type. The recipe SHALL
parse the SQL and inspect the `stmt` field of each `RawStmt` to determine the statement type (e.g., `SelectStmt`,
`InsertStmt`, `CreateStmt`).

#### Scenario: Identifies statement types

- **WHEN** the recipe cell executes with a multi-statement SQL string containing SELECT, INSERT, and CREATE TABLE
- **THEN** it displays the classified type for each statement

### Requirement: Recipe — Detect subqueries

The notebook SHALL include a recipe that detects subqueries by finding nested `SelectStmt` nodes within a parse tree.
The recipe SHALL use `walk()` to traverse the tree and identify `SelectStmt` messages that appear below the top-level
statement.

#### Scenario: Finds nested SELECT in WHERE clause

- **WHEN** the recipe cell executes with a query like `SELECT * FROM t WHERE id IN (SELECT id FROM s)`
- **THEN** it reports the presence and count of subqueries

### Requirement: Recipe — Measure query complexity

The notebook SHALL include a recipe that computes a complexity heuristic for a SQL query. The recipe SHALL count total
AST nodes, number of JOINs (via `JoinExpr`), and number of conditions (via `BoolExpr` or `A_Expr`), then produce a
summary score or breakdown.

#### Scenario: Complex query scores higher than simple query

- **WHEN** the recipe cell compares `SELECT 1` against a multi-join query with WHERE conditions
- **THEN** the complex query produces a higher complexity score

### Requirement: Recipe — Map schema dependencies

The notebook SHALL include a recipe that builds a dependency map from DDL and DML statements. The recipe SHALL parse
multiple SQL statements, extract table names from each, and display which tables are referenced together (e.g., an
INSERT that SELECTs from another table creates a dependency edge).

#### Scenario: Identifies cross-table dependency

- **WHEN** the recipe cell executes with `CREATE TABLE a (id int); INSERT INTO a SELECT * FROM b`
- **THEN** it displays a dependency showing table `a` depends on table `b`

### Requirement: Cell structure convention

Each recipe cell SHALL follow a consistent pattern: define its own SQL input, run analysis using `walk()` or `Visitor`,
and render output using `mo.md()`. Recipe cells SHALL declare their postgast dependencies as function parameters (not
re-import them). Recipe cells that do not export values to other cells SHALL return an empty tuple.

#### Scenario: Recipe cell is self-contained

- **WHEN** any individual recipe cell is examined
- **THEN** it contains its own SQL string, analysis logic, and formatted output within a single `@app.cell` function

### Requirement: Header cell

The notebook SHALL include a header cell that renders a title and brief introduction explaining the purpose of the
recipebook and how to use it (run vs edit mode).

#### Scenario: Header provides orientation

- **WHEN** a user opens the notebook
- **THEN** the first visible output is a title and introduction explaining the recipebook's purpose

### Requirement: Optional dependency configuration

The `marimo` package SHALL be declared as a dev-only dependency under a `recipes` dependency group in `pyproject.toml`,
installable via `uv sync --group recipes`.

#### Scenario: Install recipes group

- **WHEN** a user runs `uv sync --group recipes`
- **THEN** `marimo` is installed and `recipes/ast_walker.py` can be executed
