## Why

postgast exposes `parse` and (soon) `deparse` as core operations, but there is no systematic test suite verifying that
`deparse(parse(sql))` produces semantically equivalent SQL across a broad range of PostgreSQL syntax. Roundtrip tests
catch subtle bugs — lost clauses, incorrect operator precedence, broken identifier quoting — that isolated unit tests
for parse or deparse alone would miss.

## What Changes

- Add a dedicated roundtrip test module that feeds SQL statements through `parse` → `deparse` → `parse` and asserts the
  two ASTs are identical (protobuf equality)
- Cover a wide range of PostgreSQL statement types: SELECT (joins, subqueries, CTEs, window functions, aggregates), DML
  (INSERT, UPDATE, DELETE, MERGE), DDL (CREATE/ALTER/DROP for tables, indexes, views, types), and utility statements
  (EXPLAIN, COPY, SET, GRANT)
- Include edge-case coverage: quoted identifiers, mixed-case names, Unicode strings, operator precedence requiring
  parentheses, `NULL` handling, default vs explicit schemas, and complex expressions
- Tests compare parsed ASTs (not raw SQL text) since libpg_query's deparse output uses canonical formatting that differs
  from the original input

## Capabilities

### New Capabilities

- `roundtrip-testing`: Systematic parse → deparse → re-parse equivalence testing across PostgreSQL syntax categories

### Modified Capabilities

_(none — no existing spec requirements change)_

## Impact

- **New file**: `tests/postgast/test_roundtrip.py` — roundtrip test suite
- **Depends on**: `deparse` function (from the `add-deparse` change) being available
- **C API**: Exercises both `pg_query_parse_protobuf` and `pg_query_deparse_protobuf` in sequence
- **No changes** to library source code — this is a test-only change
