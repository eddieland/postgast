## Why

The existing test suite (~145 tests) covers common SQL patterns well but has almost no stress or boundary-condition
coverage. There are no tests for large inputs, deeply nested queries, exotic Unicode, null bytes, or systematic
malformed-SQL patterns. This leaves the ctypes/libpg_query boundary — where Python hands off to C — under-exercised for
the inputs most likely to trigger crashes, memory issues, or unexpected error behavior.

## What Changes

- Add stress tests that exercise scale limits: very large SQL strings, deeply nested expressions, many-statement inputs,
  and wide queries (large column/join/parameter counts)
- Add boundary-condition tests for each core operation (parse, deparse, normalize, fingerprint, split, scan): null
  bytes, control characters, zero-width Unicode, emoji/non-BMP codepoints, extremely long identifiers and string
  literals
- Add systematic malformed-input tests: unterminated constructs (strings, comments, parentheses), partial statements,
  invalid numeric literals, and garbage bytes — verifying the library raises `PgQueryError` cleanly rather than crashing
- Add error-resilience tests: sequential batches of invalid inputs to confirm no state leakage between calls

## Capabilities

### New Capabilities

- `stress-testing`: Scale and resource-limit tests — large inputs, deep nesting, high counts — across all core
  operations (parse, deparse, normalize, fingerprint, split, scan)
- `boundary-testing`: Edge-case input tests — null bytes, control characters, Unicode boundaries, malformed SQL,
  unterminated constructs — verifying clean error handling at the Python/C boundary

### Modified Capabilities

_(none — no existing spec requirements are changing)_

## Impact

- **Tests**: New test files `tests/postgast/test_stress.py` and `tests/postgast/test_boundary.py`
- **Source modules exercised**: `_parse.py`, `_deparse.py`, `_normalize.py`, `_fingerprint.py`, `_split.py`, `_scan.py`,
  `_errors.py` (all via their public API)
- **C boundary**: `_native.py` ctypes calls to `pg_query_parse`, `pg_query_deparse_protobuf`, `pg_query_normalize`,
  `pg_query_fingerprint`, `pg_query_split_with_scanner`, `pg_query_split_with_parser`, `pg_query_scan`
- **No changes to library source code or public API** — this is a test-only change
- **CI**: Test runtime will increase; stress tests should be marked so they can be excluded from fast feedback loops if
  needed
