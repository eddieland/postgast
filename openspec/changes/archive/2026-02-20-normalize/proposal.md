## Why

postgast has a complete ctypes foundation (library loading, C struct bindings, function signatures) but no public Python
API. Users cannot call any of the six core operations. `normalize` is the first public function — it is the simplest
(string-in, string-out, no protobuf) and establishes the error handling, result lifecycle, and module layout patterns
that all subsequent functions will follow.

## What Changes

- Add a custom `PgQueryError` exception class with structured fields (`message`, `cursorpos`, `context`, etc.) extracted
  from the C `PgQueryError` struct.
- Add a `normalize(query: str) -> str` function that calls `pg_query_normalize` via ctypes, handles errors, frees the C
  result, and returns a Python string.
- Establish the public API surface in `__init__.py` via re-exports.
- Add unit tests for both error handling and normalization behavior.

## Capabilities

### New Capabilities

- `error-handling`: Custom `PgQueryError` exception with structured fields, and a helper to raise from the C error
  struct. Shared by all public API functions.
- `normalize`: Public `normalize()` function that replaces SQL literal constants with parameter placeholders via
  libpg_query's `pg_query_normalize`.

### Modified Capabilities

_None._

## Impact

- **New files**: `src/postgast/_errors.py`, `src/postgast/_normalize.py`
- **Modified files**: `src/postgast/__init__.py` (re-exports `normalize` and `PgQueryError`)
- **Tests**: New test files for error handling and normalization
- **Dependencies**: No new runtime dependencies (normalize is string-in, string-out)
