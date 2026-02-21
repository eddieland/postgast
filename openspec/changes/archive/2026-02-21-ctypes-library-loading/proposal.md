## Why

postgast needs to call libpg_query's C functions, but currently has no mechanism to load the shared library or
communicate with it. Without this foundation, none of the public API functions (parse, deparse, normalize, fingerprint,
split, scan) can be implemented.

## What Changes

- Add a new internal module `src/postgast/_native.py` that loads `libpg_query` and declares ctypes bindings
- Define ctypes `Structure` classes mirroring libpg_query's C result structs (`PgQueryError`, `PgQueryParseResult`,
  `PgQueryNormalizeResult`, etc.)
- Set `argtypes` and `restype` on each C function for type-safe calls
- Handle platform-specific shared library names (`.so`, `.dylib`, `.dll`)

## Capabilities

### New Capabilities

- `native-library-loading`: Load the libpg_query shared library via ctypes with platform-aware resolution
- `c-struct-bindings`: ctypes Structure definitions for all libpg_query result types
- `function-signatures`: Declared argtypes/restype for all public C functions

### Modified Capabilities

<!-- None — this is greenfield work -->

## Impact

- `src/postgast/_native.py`: New file — all ctypes loading and struct definitions
