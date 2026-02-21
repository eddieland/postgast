## Context

postgast is a pure-Python library (no Cython/Rust/C extensions) that calls libpg_query via `ctypes`. The shared library
must be present on the user's system. This module is the lowest layer — everything else builds on it.

## Goals / Non-Goals

**Goals:**

- Load libpg_query on Linux, macOS, and Windows
- Define ctypes struct bindings matching the C API
- Declare function signatures for all public C functions
- Fail clearly if the library isn't available

**Non-Goals:**

- Bundling or compiling libpg_query (out of scope — users install it separately)
- Implementing the Python-level public API (parse, normalize, etc.) — that's a follow-up change
- Protobuf message definitions — separate concern

## Decisions

### Decision 1: Single `_native.py` internal module

All ctypes definitions live in one private module `src/postgast/_native.py`. The leading underscore signals this is not
public API. Alternatives considered: splitting structs and function declarations into separate files, but the total code
is small enough (~150 lines) to keep together.

### Decision 2: `ctypes.util.find_library` for resolution

Use `ctypes.util.find_library("pg_query")` which handles platform differences automatically, falling back to direct name
loading if needed. This is the standard Python approach and respects `LD_LIBRARY_PATH`, `DYLD_LIBRARY_PATH`, etc.

### Decision 3: Structs returned by value

libpg_query returns result structs by value (not pointers). The ctypes bindings will set `restype` to the struct type
directly. Free functions accept the struct by value as well.

## Risks / Trade-offs

- **Library not found at import time** → Deferred loading (load on first use) would be more complex but could allow
  importing postgast without libpg_query installed. We choose eager loading for simplicity — fail fast.
- **Struct layout mismatch** → If the C struct layout changes between libpg_query versions, the ctypes bindings break
  silently. Mitigated by targeting a specific version (17-6.x).
