## ADDED Requirements

### Requirement: Parse function

The module SHALL provide a `parse(query: str) -> ParseResult` function that parses a SQL string into a protobuf
`ParseResult` AST by calling libpg_query's `pg_query_parse_protobuf` C function and deserializing the binary output.

#### Scenario: Simple SELECT statement

- **WHEN** `parse` is called with `"SELECT 1"`
- **THEN** it returns a `ParseResult` with `version` set to the libpg_query PostgreSQL version number and `stmts`
  containing exactly one `RawStmt` whose `stmt` has the `select_stmt` field set

#### Scenario: Multi-statement input

- **WHEN** `parse` is called with `"SELECT 1; SELECT 2"`
- **THEN** it returns a `ParseResult` with `stmts` containing exactly two `RawStmt` entries

#### Scenario: DDL statement (CREATE TABLE)

- **WHEN** `parse` is called with `"CREATE TABLE t (id int PRIMARY KEY, name text)"`
- **THEN** it returns a `ParseResult` with one `RawStmt` whose `stmt` has the `create_stmt` field set

#### Scenario: Invalid SQL raises PgQueryError

- **WHEN** `parse` is called with syntactically invalid SQL (e.g., `"SELECT FROM"`)
- **THEN** it raises `PgQueryError` with a descriptive `message` and a `cursorpos` indicating where the error was
  detected

#### Scenario: Empty string raises PgQueryError

- **WHEN** `parse` is called with an empty string `""`
- **THEN** it returns a `ParseResult` with an empty `stmts` list

### Requirement: Binary protobuf extraction

The function SHALL extract protobuf bytes from the C result using `ctypes.string_at(data, len)` to safely handle binary
data containing null bytes, rather than relying on `c_char_p` auto-conversion.

#### Scenario: Protobuf with embedded null bytes

- **WHEN** a SQL query produces a protobuf encoding that contains `\x00` bytes
- **THEN** the full binary payload is extracted without truncation and deserialized correctly

### Requirement: Result memory is always freed

The C result struct returned by `pg_query_parse_protobuf` SHALL always be freed via
`pg_query_free_protobuf_parse_result`, regardless of whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `parse` is called with valid SQL and returns successfully
- **THEN** the C result struct is freed after extracting the protobuf bytes

#### Scenario: Memory freed on error

- **WHEN** `parse` is called with invalid SQL and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

### Requirement: Public API export

The `parse` function SHALL be importable directly from the `postgast` package (i.e., `from postgast import parse`).

#### Scenario: Top-level import

- **WHEN** user code runs `from postgast import parse`
- **THEN** the name resolves without error and is callable
