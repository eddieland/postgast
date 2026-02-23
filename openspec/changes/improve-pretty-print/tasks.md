## 1. Identifier quoting helper

- [ ] 1.1 Add `_needs_quoting(name: str) -> bool` helper to `format.py` — regex check for `[a-z_][a-z0-9_]*$` pattern,
  then `scan()`-based reserved keyword detection for matches
- [ ] 1.2 Add `_quote_ident(name: str) -> str` helper that wraps in double quotes (with `"` → `""` escaping) when
  `_needs_quoting` returns True
- [ ] 1.3 Update `visit_ColumnRef` to use `_quote_ident` for each `String` field part
- [ ] 1.4 Update `visit_RangeVar` to use `_quote_ident` for `schemaname` and `relname`
- [ ] 1.5 Update alias emission in `visit_RangeVar`, `visit_RangeSubselect`, and `visit_RangeFunction` to use
  `_quote_ident`
- [ ] 1.6 Add round-trip and output tests: reserved word column (`"order"`), reserved word table (`"user"`), mixed-case
  (`"MyColumn"`), plain identifier (no quotes)

## 2. Boolean expression parenthesization

- [ ] 2.1 Add `_needs_bool_parens(parent_op, child_node)` helper that peeks at the unwrapped child and returns True when
  the child is a `BoolExpr` with lower precedence (OR inside AND, AND/OR inside NOT)
- [ ] 2.2 Update `visit_BoolExpr` inline path to wrap lower-precedence children in parentheses
- [ ] 2.3 Update `visit_BoolExpr` clause-context path to wrap lower-precedence children in parentheses
- [ ] 2.4 Add round-trip and output tests: `(a OR b) AND (c OR d)`, `a AND (b OR c)`, `NOT (a AND b)`, flat
  `a AND b AND c` (no parens)

## 3. Window frame clause

- [ ] 3.1 Define `FRAMEOPTION_*` bitmask constants in `format.py`
- [ ] 3.2 Add `_visit_window_frame(frame_options, start_offset, end_offset)` helper to `_visit_window_def` — decode mode
  (ROWS/RANGE/GROUPS), BETWEEN, start/end bounds, and EXCLUDE
- [ ] 3.3 Call `_visit_window_frame` from `_visit_window_def` when `FRAMEOPTION_NONDEFAULT` is set
- [ ] 3.4 Add round-trip and output tests: `ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING`,
  `RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`, `GROUPS BETWEEN ...`, `ROWS UNBOUNDED PRECEDING` (no
  BETWEEN), default frame (no output)

## 4. DISTINCT ON

- [ ] 4.1 Update `visit_SelectStmt` to inspect `distinct_clause` items — if they are non-sentinel expressions, emit
  `DISTINCT ON (expr, ...)` instead of bare `DISTINCT`
- [ ] 4.2 Add round-trip and output tests: `DISTINCT ON (a)`, `DISTINCT ON (a, b)`, bare `DISTINCT` unchanged

## 5. Locking clauses

- [ ] 5.1 Replace `_deparse_node` fallback in `visit_SelectStmt`'s locking section with direct rendering: map `strength`
  enum to `FOR UPDATE`/`FOR SHARE`/`FOR NO KEY UPDATE`/`FOR KEY SHARE`, emit `OF` relations, map `wait_policy` to
  `NOWAIT`/`SKIP LOCKED`
- [ ] 5.2 Add round-trip and output tests: `FOR UPDATE`, `FOR SHARE SKIP LOCKED`, `FOR UPDATE OF t1 NOWAIT`,
  `FOR NO KEY UPDATE`

## 6. New visitor: GroupingSet

- [ ] 6.1 Add `visit_GroupingSet` — map `kind` enum to `ROLLUP(...)`, `CUBE(...)`, `GROUPING SETS(...)`, handle
  `GROUPING_SET_EMPTY` as `()` and `GROUPING_SET_SIMPLE` by visiting content directly
- [ ] 6.2 Add round-trip and output tests: `ROLLUP(a, b)`, `CUBE(a, b)`, `GROUPING SETS((a), ())`

## 7. New visitor: RangeTableSample

- [ ] 7.1 Add `visit_RangeTableSample` — emit `<relation> TABLESAMPLE <method>(<args>)` with optional
  `REPEATABLE(<expr>)`
- [ ] 7.2 Add round-trip and output tests: `TABLESAMPLE BERNOULLI(10)`, `TABLESAMPLE SYSTEM(50) REPEATABLE(42)`

## 8. New visitor: RowExpr

- [ ] 8.1 Add `visit_RowExpr` — emit `ROW(args)` for explicit `COERCE_EXPLICIT_CALL`, parenthesized args for implicit
- [ ] 8.2 Add round-trip and output tests: `ROW(1, 2, 3)`, `(1, 2, 3)` implicit row

## 9. Subquery column aliases

- [ ] 9.1 Update `visit_RangeSubselect` to emit `alias.colnames` as `(col1, col2, ...)` after alias name
- [ ] 9.2 Update `visit_RangeFunction` to emit `alias.colnames` consistently
- [ ] 9.3 Add round-trip and output tests: `AS t(a, b)` with column aliases, `AS sub` without

## 10. Function name pg_catalog stripping

- [ ] 10.1 Update `visit_FuncCall` to filter `pg_catalog` from `name_parts` before joining, matching `_visit_type_name`
  pattern
- [ ] 10.2 Add output tests: `pg_catalog.btrim(name)` → `btrim(name)`, `myschema.myfunc(1)` preserved

## 11. Final validation

- [ ] 11.1 Run full test suite (`make test`) and verify all existing tests still pass
- [ ] 11.2 Run `make lint` and fix any type-checker or linter issues
- [ ] 11.3 Verify idempotency for all new test cases
