## Why

`format_sql()` has semantic correctness bugs where formatted output parses to a different query than the input. Nested
boolean expressions lose required parentheses, window frame clauses are silently dropped, several AST node types produce
garbled output, and reserved-word identifiers lose their quoting — producing unparsable SQL. These violate the existing
spec's round-trip equivalence requirement.

## What Changes

- Fix nested `BoolExpr` to emit parentheses when a child operator has lower precedence than its parent (OR inside AND,
  AND/OR inside NOT)
- Fix `ColumnRef` and `RangeVar` to quote identifiers that are reserved words or require quoting (mixed case, special
  characters)
- Add window frame clause rendering (`frame_options`, `start_offset`, `end_offset`) to `_visit_window_def`
- Handle `DISTINCT ON (expr, ...)` in `visit_SelectStmt` instead of emitting bare `DISTINCT`
- Handle `FOR UPDATE/SHARE/NO KEY UPDATE/KEY SHARE` locking clauses directly instead of attempting `_deparse_node` on
  `LockingClause` (which libpg_query cannot deparse as a standalone statement)
- Add `visit_GroupingSet` for `ROLLUP`, `CUBE`, and `GROUPING SETS`
- Add `visit_RangeTableSample` for `TABLESAMPLE` clauses
- Add `visit_RowExpr` for `ROW(...)` constructors
- Fix `visit_RangeSubselect` to emit column aliases from `alias.colnames`
- Strip `pg_catalog.` schema prefix from function names in `visit_FuncCall` (cosmetic, matching the existing type-name
  behavior)

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `pretty-print`: Fix violations of the semantic equivalence requirement — nested boolean precedence, identifier
  quoting, window frames, DISTINCT ON, locking clauses, grouping sets, table sampling, row constructors, and subquery
  column aliases. All existing spec requirements remain; no new behavioral contracts are introduced.

## Impact

- `src/postgast/format.py` — all fixes are in the `_SqlFormatter` visitor class
- `tests/postgast/test_format.py` — new round-trip cases for each bug
- `tests/postgast/test_format_output.py` — new snapshot entries for each fix
- No new modules, dependencies, or API changes
