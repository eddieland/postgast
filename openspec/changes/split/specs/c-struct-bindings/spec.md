## ADDED Requirements

### Requirement: Split statement struct binding

The module SHALL define a `PgQuerySplitStmt` ctypes Structure with fields `stmt_location` (`c_int`) and `stmt_len`
(`c_int`), matching the C `PgQuerySplitStmt` struct from `pg_query.h`.

#### Scenario: Struct fields match C layout

- **WHEN** a `PgQuerySplitStmt` instance is populated from a C function result
- **THEN** `stmt_location` contains the byte offset of the statement start and `stmt_len` contains the byte length of
  the statement

## MODIFIED Requirements

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
