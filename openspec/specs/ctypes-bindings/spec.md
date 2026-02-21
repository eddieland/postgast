# ctypes-bindings Specification

## Purpose

Define the ctypes interface to libpg_query: load the shared library at import time, declare C struct bindings for all
result types, and set function signatures (argtypes/restype) on all public C functions.

## Requirements

### Requirement: Platform-aware library resolution

The module SHALL resolve the correct shared library for the current platform using a two-step search:

1. First, look for a vendored copy adjacent to the `_native.py` module (`libpg_query.so` on Linux, `libpg_query.dylib`
   on macOS, `pg_query.dll` on Windows).
1. If no vendored copy is found, fall back to `ctypes.util.find_library("pg_query")` for system-installed libraries.

#### Scenario: Load vendored library on Linux

- **WHEN** the module is imported on a Linux system
- **AND** `libpg_query.so` exists in the package directory
- **THEN** it loads the vendored `libpg_query.so`

#### Scenario: Load vendored library on macOS

- **WHEN** the module is imported on a macOS system
- **AND** `libpg_query.dylib` exists in the package directory
- **THEN** it loads the vendored `libpg_query.dylib`

#### Scenario: Load vendored library on Windows

- **WHEN** the module is imported on a Windows system
- **AND** `pg_query.dll` exists in the package directory
- **THEN** it loads the vendored `pg_query.dll`

#### Scenario: Fall back to system library

- **WHEN** the module is imported on any platform
- **AND** no vendored library exists in the package directory
- **THEN** it falls back to `ctypes.util.find_library("pg_query")`

#### Scenario: Load on Linux without vendored copy

- **WHEN** the module is imported on a Linux system
- **AND** no vendored `libpg_query.so` exists in the package directory
- **AND** libpg_query is installed system-wide
- **THEN** it loads the system `libpg_query.so` via `ctypes.util.find_library`

### Requirement: Library load failure raises clear error

The module SHALL raise an OSError with a descriptive message if libpg_query cannot be found via either the vendored path
or the system library search.

#### Scenario: Library not installed

- **WHEN** no vendored library exists in the package directory
- **AND** libpg_query is not installed on the system
- **THEN** an OSError is raised with a message indicating the library was not found

### Requirement: Error struct binding

The module SHALL define a ctypes Structure for PgQueryError with fields: message, funcname, filename, lineno, cursorpos,
context.

#### Scenario: Error struct field access

- **WHEN** a C function returns a result with a non-null error pointer
- **THEN** the error's message, funcname, filename, lineno, cursorpos, and context fields are accessible as Python
  attributes

### Requirement: Split statement struct binding

The module SHALL define a `PgQuerySplitStmt` ctypes Structure with fields `stmt_location` (`c_int`) and `stmt_len`
(`c_int`), matching the C `PgQuerySplitStmt` struct from `pg_query.h`.

#### Scenario: Struct fields match C layout

- **WHEN** a `PgQuerySplitStmt` instance is populated from a C function result
- **THEN** `stmt_location` contains the byte offset of the statement start and `stmt_len` contains the byte length of
  the statement

### Requirement: Result struct bindings

The module SHALL define ctypes Structures for all libpg_query result types: PgQueryParseResult,
PgQueryProtobufParseResult, PgQueryNormalizeResult, PgQueryFingerprintResult, PgQueryScanResult, PgQuerySplitResult,
PgQueryDeparseResult. The `PgQuerySplitResult.stmts` field SHALL be typed as `POINTER(POINTER(PgQuerySplitStmt))` to
match the C struct layout where `stmts` is `PgQuerySplitStmt **`.

#### Scenario: Result structs match C layout

- **WHEN** a ctypes result struct is populated by a C function call
- **THEN** its fields correspond to the C struct layout and values are correctly marshalled

#### Scenario: Split result stmts field type

- **WHEN** `PgQuerySplitResult` is used with `pg_query_split_with_scanner`
- **THEN** `stmts[i].contents` yields a `PgQuerySplitStmt` with accessible `stmt_location` and `stmt_len` attributes

### Requirement: Core function signatures declared

The module SHALL set argtypes and restype on all public libpg_query functions: pg_query_parse, pg_query_parse_protobuf,
pg_query_normalize, pg_query_fingerprint, pg_query_scan, pg_query_split_with_scanner, pg_query_deparse_protobuf, and
their corresponding pg_query_free\_\* functions.

#### Scenario: Parse function signature

- **WHEN** pg_query_parse is called via ctypes with a bytes argument
- **THEN** it returns a PgQueryParseResult struct

#### Scenario: Free function signature

- **WHEN** a pg_query_free\_\* function is called with its corresponding result struct
- **THEN** it completes without error and the result memory is released
