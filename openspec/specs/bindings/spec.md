# bindings Specification

## Purpose

Low-level infrastructure for interfacing Python with libpg_query: ctypes bindings to load and call the C shared library,
generated protobuf Python module for AST types, and structured error handling to translate C errors into Python
exceptions.

______________________________________________________________________

## ctypes Interface

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

______________________________________________________________________

## Protobuf Bindings

### Requirement: Generated protobuf module

The package SHALL include a generated Python protobuf module (`pg_query_pb2.py`) produced by running `protoc` against
the vendored `vendor/libpg_query/protobuf/pg_query.proto`. The generated file SHALL be committed to the repository so
that users installing from source do not need `protoc`.

#### Scenario: Module is importable

- **WHEN** the package is installed
- **THEN** `from postgast.pg_query_pb2 import ParseResult` succeeds without error

#### Scenario: ParseResult message structure

- **WHEN** the `ParseResult` message is inspected
- **THEN** it has an `int32 version` field and a `repeated RawStmt stmts` field matching the proto schema

### Requirement: Protobuf runtime dependency

The package SHALL declare `protobuf>=5.29` as a runtime dependency in `pyproject.toml` `dependencies`. This is the
official Google protobuf library.

#### Scenario: Dependency is installed automatically

- **WHEN** a user runs `pip install postgast`
- **THEN** the `protobuf` package is installed as a dependency

### Requirement: Makefile regeneration target

The project SHALL provide a `make proto` target that regenerates `pg_query_pb2.py` from the vendored proto file. This
target is used by maintainers when the vendored `pg_query.proto` is updated.

#### Scenario: Regeneration produces identical output

- **WHEN** `make proto` is run without modifying the vendored proto file
- **THEN** the generated `pg_query_pb2.py` is byte-identical to the committed version

#### Scenario: Regeneration reflects proto changes

- **WHEN** the vendored `pg_query.proto` is updated and `make proto` is run
- **THEN** the generated `pg_query_pb2.py` reflects the updated proto definitions

### Requirement: Protobuf module re-export

The generated protobuf module SHALL be re-exported from the `postgast` package as `postgast.pg_query_pb2` so users can
access AST node types (e.g., `from postgast.pg_query_pb2 import ParseResult, Node, SelectStmt`).

#### Scenario: Public re-export access

- **WHEN** user code runs `from postgast import pg_query_pb2`
- **THEN** the module is accessible and contains protobuf message classes

______________________________________________________________________

## Error Handling

### Requirement: PgQueryError exception class

The module SHALL provide a `PgQueryError` exception class that inherits from `Exception` and exposes structured fields
from the C `PgQueryError` struct: `message` (str), `cursorpos` (int), `context` (str | None), `funcname` (str | None),
`filename` (str | None), `lineno` (int).

#### Scenario: Exception has structured attributes

- **WHEN** a `PgQueryError` is raised due to invalid SQL
- **THEN** the exception's `message` attribute contains the error description, `cursorpos` contains the 1-based position
  in the SQL string where the error was detected, and `str(exception)` returns the message

#### Scenario: Exception is catchable

- **WHEN** user code wraps a postgast call in `try/except PgQueryError`
- **THEN** the exception is caught and its structured fields are accessible

#### Scenario: Optional fields are None when absent

- **WHEN** the C error struct has NULL values for context, funcname, or filename
- **THEN** the corresponding Python attributes SHALL be `None`

### Requirement: Error checking helper

The module SHALL provide an internal helper that inspects a C result struct's error pointer. If the error pointer is
non-null, the helper SHALL extract the error fields and raise `PgQueryError`. The caller is responsible for freeing the
C result (typically via a `finally` block).

#### Scenario: Non-null error pointer raises exception

- **WHEN** a C function returns a result with a non-null error pointer
- **THEN** the helper raises `PgQueryError` with the error fields populated

#### Scenario: Null error pointer does not raise

- **WHEN** a C function returns a result with a null error pointer
- **THEN** the helper returns without raising and the result remains available for value extraction
