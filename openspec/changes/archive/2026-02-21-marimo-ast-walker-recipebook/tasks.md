## 1. Project setup

- [x] 1.1 Add `recipes` optional dependency extra with `marimo>=0.10` to `pyproject.toml`
- [x] 1.2 Create `recipes/` directory and empty `recipes/ast_walker.py` with `marimo.App()` scaffold and `if __name__`
  block

## 2. Notebook scaffold cells

- [x] 2.1 Add header cell rendering title and introduction via `mo.md()` (explain purpose, run vs edit mode)
- [x] 2.2 Add shared imports cell exporting `parse`, `deparse`, `walk`, `Visitor`, `pg_query_pb2`, and `mo`

## 3. Recipe cells — basic patterns

- [x] 3.1 Add "Extract table names" recipe: `Visitor` subclass with `visit_RangeVar` collecting `relname` values from a
  multi-JOIN query
- [x] 3.2 Add "Collect column references" recipe: `walk()` generator filtering for `ColumnRef` types and extracting
  column names from `fields`
- [x] 3.3 Add "Classify statement type" recipe: inspect `RawStmt.stmt` to identify `SelectStmt`, `InsertStmt`,
  `CreateStmt` across a multi-statement input

## 4. Recipe cells — advanced patterns

- [x] 4.1 Add "Detect subqueries" recipe: `walk()` to find nested `SelectStmt` nodes below the top-level statement,
  report count
- [x] 4.2 Add "Measure query complexity" recipe: count total AST nodes, `JoinExpr` joins, `BoolExpr`/`A_Expr`
  conditions; compare simple vs complex query scores
- [x] 4.3 Add "Map schema dependencies" recipe: parse DDL+DML statements, extract table names per statement, display
  dependency edges

## 5. Verify

- [x] 5.1 Run `uv sync --extra recipes` and verify marimo installs
- [x] 5.2 Execute `uv run python recipes/ast_walker.py` and confirm all cells run without error
- [x] 5.3 Run `make fmt` to ensure the notebook passes linting
