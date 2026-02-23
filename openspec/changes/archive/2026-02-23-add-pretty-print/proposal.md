## Why

postgast can parse SQL into an AST and deparse it back, but `deparse()` delegates to libpg_query's C deparser which
produces a single canonical line — no indentation, no line breaks, no visual structure. A complex query like:

```sql
SELECT u.id, u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'active' AND o.total > 100 GROUP BY u.id, u.name HAVING count(*) > 1 ORDER BY o.total DESC LIMIT 50
```

is unreadable compared to:

```sql
SELECT
  u.id,
  u.name,
  o.total
FROM
  users u
  JOIN orders o ON u.id = o.user_id
WHERE
  o.status = 'active'
  AND o.total > 100
GROUP BY
  u.id,
  u.name
HAVING
  count(*) > 1
ORDER BY
  o.total DESC
LIMIT
  50
```

Pretty printing is a common need for SQL tooling — migration reviewers, linters, code generators, and interactive
notebooks all benefit from readable formatting. Today, users must reach for an external formatter (pgFormatter,
sqlfluff, pg_format) even though postgast already has the parsed AST.

The philosophy is **Black for SQL**: one canonical format, no configuration knobs, deterministic output. Users should
not argue about SQL style — the formatter decides. Configuration can be introduced later (line width, keyword casing,
etc.) but the first version is opinionated and zero-config.

## What Changes

Add a `format_sql()` function that accepts a SQL string (or `ParseResult`) and returns a pretty-printed SQL string. The
implementation walks the protobuf AST and emits formatted SQL directly — it does **not** call libpg_query's C deparser.

The formatter is a pure-Python AST visitor that handles each statement type (SELECT, INSERT, UPDATE, DELETE, CREATE
TABLE, etc.) with clause-level indentation and line-break rules. It is not a string-level reformatter — it understands
SQL structure because it operates on the parsed tree.

Initial formatting rules (the "one right way"):

- **Uppercase keywords** (SELECT, FROM, WHERE, JOIN, etc.)
- **Clause-per-line**: each major clause starts on a new line at column 0
- **Indented clause bodies**: items within a clause are indented by 2 spaces
- **One item per line** in SELECT lists, GROUP BY, ORDER BY when there are multiple items
- **Subqueries indented**: nested SELECT blocks get one additional indent level
- **Trailing commas**: no trailing commas (standard SQL style)
- **Parenthesized expressions**: kept inline when short, broken across lines when long
- **Semicolons**: each statement ends with a semicolon, separated by blank lines

## Capabilities

### New Capabilities

- `pretty-print`: Format SQL strings into a canonical, readable layout by walking the protobuf AST and emitting
  structured output. Supports SELECT, INSERT, UPDATE, DELETE, and common DDL statements. Zero configuration — one
  deterministic format.

### Modified Capabilities

None. The existing `deparse()` function is unchanged. `format_sql()` is a new, independent function.

## Impact

- `src/postgast/format.py` (new) — AST-walking SQL formatter
- `src/postgast/__init__.py` (modified) — re-export `format_sql`
- `tests/test_format.py` (new) — formatting tests (round-trip validity, snapshot-style expected output)
