## Context

postgast currently has focused unit tests for `parse` and `normalize` that verify individual function behavior. The
`add-deparse` change introduces `deparse`, completing the parse → deparse cycle. With both directions available, we need
a test suite that verifies the full roundtrip: SQL in, AST out, SQL back, AST again — confirming no information is lost
or corrupted in the cycle.

The existing test files (`test_parse.py`, `test_normalize.py`) each follow the pattern of a single test class with
`pytest`, importing directly from `postgast`. Roundtrip tests will follow the same conventions.

## Goals / Non-Goals

**Goals:**

- Verify `parse(deparse(parse(sql)))` produces an AST identical to `parse(sql)` for a broad set of PostgreSQL syntax
- Organize test cases by SQL category for easy identification of which syntax areas fail
- Make it trivial to add new SQL examples as coverage expands

**Non-Goals:**

- Testing deparse output formatting or style (that belongs in deparse unit tests)
- Comparing SQL text strings for equality (libpg_query canonicalizes output)
- Achieving exhaustive PostgreSQL grammar coverage — focus on commonly-used syntax
- Integration tests against a live PostgreSQL instance (roundtrip is purely in-process)

## Decisions

### 1. Equivalence via double-parse AST comparison

Compare `parse(sql)` to `parse(deparse(parse(sql)))`. Both sides produce a `ParseResult` protobuf, which supports
equality comparison. This avoids fragile string matching and directly tests what matters: semantic preservation.

**Alternative considered**: Compare deparsed SQL strings. Rejected because libpg_query's deparse produces canonical
formatting (e.g., added parentheses, uppercased keywords) that differs from the original input. String comparison would
require a normalization layer with no additional benefit over AST comparison.

### 2. Parametrized tests grouped by SQL category

Use `@pytest.mark.parametrize` with a list of SQL strings per category (SELECT, DML, DDL, utility, edge cases). Each
category is a separate test method, so failures clearly indicate which syntax area broke.

**Alternative considered**: One giant parametrize list across all categories. Rejected because a failure in DDL would be
indistinguishable from a failure in SELECT without reading the SQL string.

### 3. Shared `assert_roundtrip` helper

Extract the `parse → deparse → re-parse → assert equal` logic into a module-level helper function. Every test case calls
the same helper, keeping the test methods purely about declaring SQL inputs. The helper takes a SQL string, runs the
roundtrip, and asserts equality — raising a clear `AssertionError` with both the original and roundtripped SQL on
failure.

### 4. Unit tests only (no `@pytest.mark.integration`)

Roundtrip tests run entirely in-process via ctypes calls to the vendored libpg_query. No Docker or PostgreSQL instance
is required. Tests go in `tests/postgast/test_roundtrip.py` alongside existing unit tests.

## Risks / Trade-offs

- **Deparse dependency**: Tests cannot run until `deparse` is implemented. → Mitigation: this change is sequenced after
  `add-deparse`. If run before deparse exists, tests will fail at import time with a clear error.
- **libpg_query deparse limitations**: Some PostgreSQL syntax may not roundtrip through libpg_query's deparse (e.g.,
  vendor-specific extensions, very new syntax). → Mitigation: document known limitations; skip or xfail specific cases
  as discovered.
- **Protobuf equality semantics**: Protobuf messages compare field-by-field including default values. The `version`
  field and statement positions (`stmt_location`, `stmt_len`) will be identical on both sides since we're comparing two
  `parse()` results. → No mitigation needed — this works in our favor.
