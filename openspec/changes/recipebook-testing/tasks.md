## 1. Create test file with AST walker recipe tests

- [ ] 1.1 Create `tests/postgast/test_recipes.py` with `TestAstWalkerRecipes` class
- [ ] 1.2 Add test: Visitor subclass with `visit_RangeVar` collects table names from multi-JOIN query
- [ ] 1.3 Add test: `walk()` filtering for `ColumnRef` nodes extracts column names via `fields[].string.sval`
- [ ] 1.4 Add test: `stmt.WhichOneof("node")` classifies statement types from multi-statement SQL
- [ ] 1.5 Add test: `walk()` detects nested `SelectStmt` nodes as subqueries (skipping top-level)
- [ ] 1.6 Add test: complexity measurement counts nodes, `JoinExpr`, `BoolExpr`/`A_Expr` — complex > simple
- [ ] 1.7 Add test: dependency mapping extracts edges from INSERT/CREATE statements referencing multiple tables
- [ ] 1.8 Add test: `extract_tables`, `extract_columns`, `extract_functions`, `find_nodes` return correct results
- [ ] 1.9 Add test: per-statement analysis with helpers extracts type, tables, columns, functions per statement

## 2. Add batch processing recipe tests

- [ ] 2.1 Add `TestBatchProcessingRecipes` class
- [ ] 2.2 Add test: `split()` + `parse()` on multi-statement migration yields correct statement types and tables
- [ ] 2.3 Add test: `scan()` returns tokens with valid type, keyword_kind, and byte positions
- [ ] 2.4 Add test: `normalize()` and `fingerprint()` group structurally equivalent queries
- [ ] 2.5 Add test: `find_nodes` on CREATE TABLE locates `Constraint` nodes with `pktable` for FK dependencies
- [ ] 2.6 Add test: `scan()` identifies `SQL_COMMENT` and `C_COMMENT` tokens with correct byte positions
- [ ] 2.7 Add test: batch parse with error handling — valid statements classified, invalid raises `PgQueryError`

## 3. Add SQL transforms recipe tests

- [ ] 3.1 Add `TestSqlTransformsRecipes` class
- [ ] 3.2 Add test: `deparse(parse(sql))` produces identical canonical output for cosmetic SQL variants
- [ ] 3.3 Add test: `normalize()` replaces literals with `$N` placeholders, same structure → same template
- [ ] 3.4 Add test: `fingerprint()` — same structure gives same hex, different structure gives different hex
- [ ] 3.5 Add test: `find_nodes` + modify `RangeVar.schemaname`/`relname` + `deparse` reflects changes
- [ ] 3.6 Add test: `set_or_replace` returns count > 0 for FUNCTION/VIEW/TRIGGER, deparsed has OR REPLACE
- [ ] 3.7 Add test: `set_or_replace` returns 0 for CREATE TABLE, output unchanged
- [ ] 3.8 Add test: `parse()` on invalid SQL raises `PgQueryError` with truthy `message` and `cursorpos > 0`

## 4. Validate

- [ ] 4.1 Run `uv run pytest tests/postgast/test_recipes.py -v` — all tests pass
- [ ] 4.2 Run `make lint` — no type errors or lint issues
- [ ] 4.3 Run `make test` — full test suite still passes
