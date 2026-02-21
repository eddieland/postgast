## 1. Core Implementation

- [x] 1.1 Create `src/postgast/helpers.py` with `find_nodes(tree, node_type)` — walk tree, yield all messages matching
  the given descriptor name; return a `Generator`
- [x] 1.2 Add `extract_tables()` to `helpers.py` — use `find_nodes` to collect `RangeVar` nodes, return `list[str]` with
  dot-joined `schemaname.relname`
- [x] 1.3 Add `extract_columns()` to `helpers.py` — use `find_nodes` to collect `ColumnRef` nodes, unwrap `fields` to
  `String.sval`, join with dots, represent `A_Star` as `"*"`
- [x] 1.4 Add `extract_functions()` to `helpers.py` — use `find_nodes` to collect `FuncCall` nodes, unwrap `funcname` to
  `String.sval`, join with dots

## 2. Package Exports

- [x] 2.1 Update `src/postgast/__init__.py` to import and re-export `find_nodes`, `extract_tables`, `extract_columns`,
  `extract_functions` from `helpers`; add to `__all__`

## 3. Tests

- [x] 3.1 Create `tests/postgast/test_helpers.py` with tests for `find_nodes` — finds matching nodes, empty result for
  no matches, works on subtrees, lazy evaluation
- [x] 3.2 Add tests for `extract_tables` — simple table, schema-qualified, joins, subquery, DML targets, duplicate
  references
- [x] 3.3 Add tests for `extract_columns` — simple columns, table-qualified, star, qualified star, WHERE clause columns
- [x] 3.4 Add tests for `extract_functions` — simple call, multiple calls, schema-qualified, nested calls
- [x] 3.5 Add test that helpers work on subtree nodes (not just `ParseResult`)

## 4. Validation

- [x] 4.1 Run `make lint` and fix any type-check or formatting issues
- [x] 4.2 Run `make test-unit` and verify all tests pass
