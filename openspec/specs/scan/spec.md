## ADDED Requirements

### Requirement: Scan function

The module SHALL provide a `scan(sql: str) -> ScanResult` function that tokenizes a SQL string by calling libpg_query's
`pg_query_scan` C function and deserializing the binary output into a protobuf `ScanResult` message containing a list of
`ScanToken` objects.

#### Scenario: Simple SELECT statement

- **WHEN** `scan` is called with `"SELECT 1"`
- **THEN** it returns a `ScanResult` with `version` set to the libpg_query PostgreSQL version number and `tokens`
  containing tokens for `SELECT` (a reserved keyword) and `1` (an integer constant `ICONST`)

#### Scenario: Token positions are byte offsets

- **WHEN** `scan` is called with `"SELECT 1"`
- **THEN** each `ScanToken` in the result has `start` and `end` fields representing byte offsets into the original SQL
  string, where `start` is inclusive and `end` is exclusive

#### Scenario: Keyword classification

- **WHEN** `scan` is called with SQL containing reserved keywords (e.g., `SELECT`, `FROM`), unreserved keywords (e.g.,
  `ABORT`, `ACTION`), and non-keyword tokens (e.g., identifiers, literals)
- **THEN** each `ScanToken` has a `keyword_kind` field set to the appropriate `KeywordKind` enum value:
  `RESERVED_KEYWORD`, `UNRESERVED_KEYWORD`, `COL_NAME_KEYWORD`, `TYPE_FUNC_NAME_KEYWORD`, or `NO_KEYWORD`

#### Scenario: Operators and punctuation

- **WHEN** `scan` is called with `"SELECT 1 + 2"`
- **THEN** the tokens include the `+` operator with the appropriate `Token` enum value

#### Scenario: String literals

- **WHEN** `scan` is called with `"SELECT 'hello'"`
- **THEN** the tokens include a string constant token with `token` set to `SCONST`

#### Scenario: Comments are tokenized

- **WHEN** `scan` is called with `"SELECT 1 -- comment"`
- **THEN** the tokens include a `SQL_COMMENT` token covering the comment text

#### Scenario: Multi-byte UTF-8 input

- **WHEN** `scan` is called with SQL containing multi-byte UTF-8 characters (e.g., `"SELECT 'café'"`)
- **THEN** the `start` and `end` positions are byte offsets (not character offsets), and the full token list is returned
  without error

#### Scenario: Empty string

- **WHEN** `scan` is called with an empty string `""`
- **THEN** it returns a `ScanResult` with an empty `tokens` list

### Requirement: Error handling

The function SHALL raise `PgQueryError` when libpg_query reports a scan error, with structured fields (`message`,
`cursorpos`, etc.) populated from the C error struct.

#### Scenario: Unterminated string literal

- **WHEN** `scan` is called with `"SELECT 'unterminated"`
- **THEN** it raises `PgQueryError` with a descriptive `message`

### Requirement: Binary protobuf extraction

The function SHALL extract protobuf bytes from the C result using `ctypes.string_at(data, len)` to safely handle binary
data containing null bytes, rather than relying on `c_char_p` auto-conversion.

#### Scenario: Protobuf with embedded null bytes

- **WHEN** a SQL query produces a protobuf encoding that contains `\x00` bytes
- **THEN** the full binary payload is extracted without truncation and deserialized correctly

### Requirement: Result memory is always freed

The C result struct returned by `pg_query_scan` SHALL always be freed via `pg_query_free_scan_result`, regardless of
whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `scan` is called with valid SQL and returns successfully
- **THEN** the C result struct is freed after extracting the protobuf bytes

#### Scenario: Memory freed on error

- **WHEN** `scan` is called with invalid SQL and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

### Requirement: Public API export

The `scan` function SHALL be importable directly from the `postgast` package (i.e., `from postgast import scan`).

#### Scenario: Top-level import

- **WHEN** user code runs `from postgast import scan`
- **THEN** the name resolves without error and is callable
