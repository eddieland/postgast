# c-struct-bindings Specification

## Purpose

TBD - created by archiving change ctypes-library-loading. Update Purpose after archive.

## Requirements

### Requirement: Error struct binding

The module SHALL define a ctypes Structure for PgQueryError with fields: message, funcname, filename, lineno, cursorpos,
context.

#### Scenario: Error struct field access

- **WHEN** a C function returns a result with a non-null error pointer
- **THEN** the error's message, funcname, filename, lineno, cursorpos, and context fields are accessible as Python
  attributes

### Requirement: Result struct bindings

The module SHALL define ctypes Structures for all libpg_query result types: PgQueryParseResult,
PgQueryProtobufParseResult, PgQueryNormalizeResult, PgQueryFingerprintResult, PgQueryScanResult, PgQuerySplitResult,
PgQueryDeparseResult.

#### Scenario: Result structs match C layout

- **WHEN** a ctypes result struct is populated by a C function call
- **THEN** its fields correspond to the C struct layout and values are correctly marshalled
