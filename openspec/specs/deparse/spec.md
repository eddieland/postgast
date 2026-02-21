### Requirement: Deparse function

The module SHALL provide a `deparse(tree: ParseResult) -> str` function that converts a protobuf `ParseResult` AST back
into a SQL string by serializing the protobuf, passing it to libpg_query's `pg_query_deparse_protobuf` C function, and
returning the resulting SQL text.

#### Scenario: Simple SELECT round-trip

- **WHEN** `deparse` is called with the `ParseResult` from `parse("SELECT 1")`
- **THEN** it returns a string containing valid SQL equivalent to `SELECT 1`

#### Scenario: SELECT with WHERE clause

- **WHEN** `deparse` is called with the `ParseResult` from `parse("SELECT id, name FROM users WHERE active = true")`
- **THEN** it returns a string containing valid SQL that is semantically equivalent to the original query

#### Scenario: DDL statement (CREATE TABLE)

- **WHEN** `deparse` is called with the `ParseResult` from `parse("CREATE TABLE t (id int PRIMARY KEY, name text)")`
- **THEN** it returns a string containing a valid `CREATE TABLE` statement

#### Scenario: Multi-statement input

- **WHEN** `deparse` is called with the `ParseResult` from `parse("SELECT 1; SELECT 2")`
- **THEN** it returns a string containing both statements separated by a semicolon

### Requirement: Protobuf serialization to C struct

The function SHALL serialize the `ParseResult` protobuf message using `SerializeToString()`, construct a
`PgQueryProtobuf` C struct with the serialized bytes, and pass it to `pg_query_deparse_protobuf`. The serialized bytes
reference MUST be kept alive for the duration of the C call.

#### Scenario: Protobuf bytes are correctly passed to C

- **WHEN** `deparse` is called with a valid `ParseResult`
- **THEN** the protobuf is serialized, wrapped in a `PgQueryProtobuf` struct with correct `len` and `data` fields, and
  passed to the C function

### Requirement: Result memory is always freed

The C result struct returned by `pg_query_deparse_protobuf` SHALL always be freed via `pg_query_free_deparse_result`,
regardless of whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `deparse` is called with a valid `ParseResult` and returns successfully
- **THEN** the C result struct is freed after extracting the SQL string

#### Scenario: Memory freed on error

- **WHEN** `deparse` is called with an invalid protobuf and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

### Requirement: Error handling

The function SHALL raise `PgQueryError` when the C function returns an error (e.g., when given an invalid or malformed
protobuf input). Error detection SHALL use the shared `check_error` helper.

#### Scenario: Invalid protobuf raises PgQueryError

- **WHEN** `deparse` is called with a `ParseResult` that the C deparser cannot process
- **THEN** it raises `PgQueryError` with a descriptive error message

### Requirement: Public API export

The `deparse` function SHALL be importable directly from the `postgast` package (i.e., `from postgast import deparse`).

#### Scenario: Top-level import

- **WHEN** user code runs `from postgast import deparse`
- **THEN** the name resolves without error and is callable
