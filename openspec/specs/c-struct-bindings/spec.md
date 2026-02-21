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
