## Why

The project README lists fingerprint as a core operation and the feature matrix marks it as "Planned." The ctypes
bindings for `pg_query_fingerprint` are already declared in `_native.py`, but no public Python function exposes them.
Adding `fingerprint()` completes another piece of the public API.

## What Changes

- Add a `fingerprint()` public function that accepts a SQL string and returns its libpg_query fingerprint (both the
  uint64 hash and its hex string representation)
- Export `fingerprint` from `postgast.__init__`
- Add unit tests following the existing test patterns

## Capabilities

### New Capabilities

- `fingerprint`: SQL string fingerprinting via `pg_query_fingerprint`. Accepts a SQL query, returns a structured result
  containing the numeric fingerprint and its hex string representation. Raises `PgQueryError` on invalid input.

### Modified Capabilities

_(none — the C struct binding and function signature already exist in `_native.py`)_

## Impact

- **New files**: `src/postgast/_fingerprint.py`, `tests/postgast/test_fingerprint.py`
- **Modified files**: `src/postgast/__init__.py` (add `fingerprint` to exports)
- **Dependencies**: None new — uses existing `_native.lib`, `check_error`, ctypes
- **Breaking changes**: None — purely additive
