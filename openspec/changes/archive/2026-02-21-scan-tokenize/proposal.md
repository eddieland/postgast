## Why

The C bindings for `pg_query_scan` are already wired up in `_native.py`, and the protobuf types (`ScanResult`,
`ScanToken`, `Token`, `KeywordKind`) are generated, but no Python function exposes this to users. Scan/tokenize is the
last core libpg_query operation without a public API — parse, deparse, normalize, split, and fingerprint all have (or
are getting) wrappers.

## What Changes

- Add a `scan(sql: str) -> ScanResult` function that calls `pg_query_scan`, deserializes the protobuf result, and
  returns the token list
- Export `scan` from `postgast.__init__`
- Add unit tests covering token types, keyword classification, positions, error handling, and edge cases

## Capabilities

### New Capabilities

- `scan`: Tokenize a SQL string into a sequence of `ScanToken` objects with token type, keyword kind, and byte positions

### Modified Capabilities

_(none)_

## Impact

- **New file**: `src/postgast/_scan.py` — scan function implementation
- **Modified file**: `src/postgast/__init__.py` — add `scan` to `__all__` and import
- **New file**: `tests/postgast/test_scan.py` — unit tests
- **Depends on**: existing `_native.py` (C bindings), `_errors.py` (error handling), `_pg_query_pb2.py` (protobuf types)
