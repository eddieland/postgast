## Context

`format_sql()` was shipped as a v1 pretty-printer with visitor methods for common SQL constructs. Testing focused on
round-trip equivalence for the handled patterns, but several AST node types were never given explicit visitors and fall
through to `generic_visit`, which concatenates child text without structure. More critically, the `BoolExpr` visitor
emits children without parentheses, which changes operator precedence for nested AND/OR/NOT expressions.

All fixes are confined to `_SqlFormatter` in `src/postgast/format.py`. No new modules, dependencies, or public API
changes.

## Goals / Non-Goals

**Goals:**

- Restore round-trip semantic equivalence for all SQL constructs identified in the proposal
- Every fix must pass the existing oracle: `deparse(parse(format_sql(sql))) == deparse(parse(sql))`
- Fixes must preserve idempotency: `format_sql(format_sql(sql)) == format_sql(sql)`

**Non-Goals:**

- Formatting style changes (indentation, keyword casing, line-break rules) — out of scope
- Performance optimization — the fixes add negligible overhead
- New public API surface — all changes are internal to the formatter

## Decisions

### 1. BoolExpr parenthesization: precedence-aware wrapping

SQL operator precedence: NOT > AND > OR. When a child BoolExpr has lower precedence than its parent, parentheses are
required.

**Approach:** Before visiting each BoolExpr argument, peek at the unwrapped child. If it's a `BoolExpr` whose operator
has lower precedence, emit `(`, visit, emit `)`. Concretely:

- AND parent: wrap child if it's OR
- NOT parent: wrap child if it's AND or OR
- OR parent: never wrap (OR is lowest precedence)

This applies in both inline and clause-per-line contexts. In clause context, parenthesized groups render their internals
on separate lines within the parens.

**Alternative considered:** Always parenthesize nested BoolExpr. Rejected because it over-parenthesizes `a AND b AND c`
(which is flat in the AST, not nested) and produces cluttered output for the common case.

### 2. Identifier quoting: regex + scan-based detection

The AST stores bare identifier text (`sval`) with no "was-quoted" flag. We need to re-derive quoting from the text.

**Approach:** A `_needs_quoting(name: str) -> bool` helper used by `visit_ColumnRef`, `visit_RangeVar`, and anywhere
else identifiers are emitted. The check:

1. If the name doesn't match `[a-z_][a-z0-9_]*$` → needs quoting (catches uppercase, spaces, digits-at-start, special
   chars, unicode)
1. If it does match, use `scan(f"SELECT {name}")` to check whether the second token has
   `keyword_kind == RESERVED_KEYWORD` → needs quoting (catches reserved words like `order`, `user`, `select`)

When quoting, emit `"name"` with any embedded `"` doubled to `""`.

**Alternative considered:** Maintain a hardcoded set of PostgreSQL reserved words. Rejected because it requires manual
maintenance and can drift from the bundled libpg_query version. The scan-based approach is always correct for the
specific libpg_query linked at runtime.

**Performance note:** `scan()` is a C call via ctypes and is fast. For hot paths, results could be cached with an LRU,
but this is a non-goal for now — formatting is not performance-critical.

### 3. Window frame clause: decode the frame_options bitmask

`WindowDef.frame_options` is an integer bitmask matching PostgreSQL's `FRAMEOPTION_*` constants from
`src/include/nodes/parsenodes.h`. The formatter currently ignores it entirely.

**Approach:** Define the bitmask constants in `format.py` and decode them in `_visit_window_def`:

- Check `FRAMEOPTION_NONDEFAULT` — if not set, skip frame rendering (it's the implicit default)
- Emit the mode: `ROWS` / `RANGE` / `GROUPS` based on which bit is set
- If `FRAMEOPTION_BETWEEN` is set, emit `BETWEEN <start> AND <end>`; otherwise emit just `<start>`
- Decode start/end from the appropriate flag bits (UNBOUNDED PRECEDING, CURRENT ROW, OFFSET PRECEDING, OFFSET FOLLOWING,
  UNBOUNDED FOLLOWING), emitting `start_offset`/`end_offset` node values when the offset variants are flagged
- Handle `EXCLUDE` options (CURRENT ROW, GROUP, TIES) if the corresponding bits are set

### 4. Locking clauses: direct rendering instead of deparse fallback

`LockingClause` cannot be deparsed as a standalone statement — libpg_query's deparser expects it embedded in a SELECT.
The current code wraps it in `_deparse_node()` which creates a bare `ParseResult`, causing the crash.

**Approach:** Render locking clauses directly from the protobuf fields in `visit_SelectStmt`:

- Map `strength` enum → `FOR KEY SHARE` / `FOR SHARE` / `FOR NO KEY UPDATE` / `FOR UPDATE`
- If `locked_rels` is non-empty, emit `OF table1, table2, ...`
- Map `wait_policy` enum → `NOWAIT` / `SKIP LOCKED` (omit for default `LockWaitBlock`)

### 5. Missing visitor methods: GroupingSet, RangeTableSample, RowExpr

These node types fall through to `generic_visit`, which calls `_deparse_node`. For some (like GroupingSet), deparse also
fails because the node can't stand alone. For others (like RangeTableSample), the deparse concatenation garbles output.

**Approach:** Add dedicated visitor methods:

- **`visit_GroupingSet`**: Map `kind` enum → `ROLLUP(...)` / `CUBE(...)` / `GROUPING SETS(...)`, with
  `GROUPING_SET_EMPTY` emitting `()` and `GROUPING_SET_SIMPLE` visiting content directly.
- **`visit_RangeTableSample`**: Emit `<relation> TABLESAMPLE <method>(<args>)`, plus optional `REPEATABLE(<expr>)`.
- **`visit_RowExpr`**: Emit `ROW(<args>)`. When `row_format == COERCE_EXPLICIT_CALL`, emit the `ROW` keyword; when
  `COERCE_IMPLICIT_CAST`, emit just parenthesized args.

### 6. DISTINCT ON: emit expressions from distinct_clause

The current code checks `if node.distinct_clause:` and emits `DISTINCT` but never inspects the list contents. An empty
`distinct_clause` means `DISTINCT`; a populated list means `DISTINCT ON (expr, ...)`.

**Approach:** After emitting `DISTINCT`, check whether the distinct_clause items are `Null`-typed (sentinel for bare
DISTINCT) or actual expressions. If actual expressions, emit `ON (` followed by the formatted expressions `)`.

### 7. Subquery column aliases: emit alias.colnames

`visit_RangeSubselect` currently emits `AS aliasname` but ignores `alias.colnames`. Fix: if `colnames` is non-empty,
append `(col1, col2, ...)` after the alias name.

Also apply the same fix to `visit_RangeFunction` for consistency.

### 8. pg_catalog prefix stripping in FuncCall

`visit_FuncCall` joins all `funcname` parts with `.`. When libpg_query canonicalizes `trim()` to `pg_catalog.btrim()`,
the prefix leaks through.

**Approach:** Filter out `pg_catalog` from `name_parts` before joining, matching the existing pattern in
`_visit_type_name` which already does this for types.

## Risks / Trade-offs

- **Identifier quoting is necessary in nearly all positions** — Reserved words change semantics when unquoted in most
  positions (e.g., bare `user` means `CURRENT_USER`, bare `all` means `SELECT ALL`). The only position where quoting is
  technically optional is column aliases after `AS`, but `deparse()` itself re-quotes reserved words there too. Our
  approach matches PostgreSQL's canonical deparse output. → Non-issue in practice.

- **Window frame bitmask constants are PostgreSQL-version-specific** — The bit values are defined in PostgreSQL headers
  and could theoretically change between major versions. → Mitigated: libpg_query pins to a specific PostgreSQL version,
  and the constants have been stable since PostgreSQL 11.

- **`scan()` call per identifier adds overhead** — Each `_needs_quoting` call for a novel identifier invokes the C
  scanner. → Mitigated: formatting is not a hot path, and the C call is sub-microsecond. Can add caching later if
  needed.
