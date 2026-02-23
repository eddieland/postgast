# operations Specification

## Purpose

Public functions that call libpg_query's C API to parse, deparse, normalize, fingerprint, split, and scan PostgreSQL
SQL. Each function follows a common pattern: encode input, call the C function, extract the result, free the C memory,
and raise `PgQueryError` on failure.

## Common Requirements

### Requirement: Result memory is always freed

Every operation SHALL free the C result struct returned by its corresponding libpg_query function (via the appropriate
`pg_query_free_*` function), regardless of whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** any operation is called with valid input and returns successfully
- **THEN** the C result struct is freed after extracting the return value

#### Scenario: Memory freed on error

- **WHEN** any operation is called with input that causes a C-level error
- **THEN** the C result struct is freed before the `PgQueryError` exception propagates

### Requirement: Public API export

All operation functions SHALL be importable directly from the `postgast` package (e.g.,
`from postgast import parse, deparse, normalize, fingerprint, split, scan`).

______________________________________________________________________

## parse

### Requirement: Parse function

The module SHALL provide a `parse(query: str) -> ParseResult` function that parses a SQL string into a protobuf
`ParseResult` AST by calling libpg_query's `pg_query_parse_protobuf` C function and deserializing the binary output.

The C result is freed via `pg_query_free_protobuf_parse_result`.

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

#### Scenario: Empty string

- **WHEN** `parse` is called with an empty string `""`
- **THEN** it returns a `ParseResult` with an empty `stmts` list

### Requirement: Binary protobuf extraction

The function SHALL extract protobuf bytes from the C result using `ctypes.string_at(data, len)` to safely handle binary
data containing null bytes, rather than relying on `c_char_p` auto-conversion.

#### Scenario: Protobuf with embedded null bytes

- **WHEN** a SQL query produces a protobuf encoding that contains `\x00` bytes
- **THEN** the full binary payload is extracted without truncation and deserialized correctly

______________________________________________________________________

## deparse

### Requirement: Deparse function

The module SHALL provide a `deparse(tree: ParseResult) -> str` function that converts a protobuf `ParseResult` AST back
into a SQL string by serializing the protobuf, passing it to libpg_query's `pg_query_deparse_protobuf` C function, and
returning the resulting SQL text.

The C result is freed via `pg_query_free_deparse_result`.

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

### Requirement: Error handling

The function SHALL raise `PgQueryError` when the C function returns an error (e.g., when given an invalid or malformed
protobuf input). Error detection SHALL use the shared `check_error` helper.

#### Scenario: Invalid protobuf raises PgQueryError

- **WHEN** `deparse` is called with a `ParseResult` that the C deparser cannot process
- **THEN** it raises `PgQueryError` with a descriptive error message

______________________________________________________________________

## normalize

### Requirement: Normalize function

The module SHALL provide a `normalize(query: str) -> str` function that replaces literal constants in a SQL query with
parameter placeholders (`$1`, `$2`, ...) by calling libpg_query's `pg_query_normalize` C function.

The C result is freed via `pg_query_free_normalize_result`.

#### Scenario: Simple query normalization

- **WHEN** `normalize` is called with `"SELECT * FROM t WHERE id = 42"`
- **THEN** it returns `"SELECT * FROM t WHERE id = $1"`

#### Scenario: Multiple constants normalized

- **WHEN** `normalize` is called with `"SELECT * FROM t WHERE id = 42 AND name = 'foo'"`
- **THEN** it returns a string with both constants replaced by sequential placeholders

#### Scenario: Query with no constants

- **WHEN** `normalize` is called with `"SELECT * FROM t"`
- **THEN** it returns the query unchanged

#### Scenario: Invalid SQL raises PgQueryError

- **WHEN** `normalize` is called with syntactically invalid SQL
- **THEN** it raises `PgQueryError` with a descriptive `message` and a `cursorpos` indicating where the error was
  detected

______________________________________________________________________

## fingerprint

### Requirement: Fingerprint function

The module SHALL provide a `fingerprint(query: str) -> FingerprintResult` function that computes a structural
fingerprint of a SQL query by calling libpg_query's `pg_query_fingerprint` C function. The fingerprint identifies
structurally equivalent queries regardless of literal values.

The C result is freed via `pg_query_free_fingerprint_result`.

#### Scenario: Simple query fingerprint

- **WHEN** `fingerprint` is called with `"SELECT 1"`
- **THEN** it returns a `FingerprintResult` with a non-zero `fingerprint` integer and a non-empty `hex` string

#### Scenario: Structurally equivalent queries produce the same fingerprint

- **WHEN** `fingerprint` is called with `"SELECT * FROM t WHERE id = 1"` and then with `"SELECT * FROM t WHERE id = 2"`
- **THEN** both calls return the same `fingerprint` value and the same `hex` value

#### Scenario: Structurally different queries produce different fingerprints

- **WHEN** `fingerprint` is called with `"SELECT 1"` and then with `"SELECT * FROM t"`
- **THEN** the two calls return different `fingerprint` values

#### Scenario: Invalid SQL raises PgQueryError

- **WHEN** `fingerprint` is called with syntactically invalid SQL
- **THEN** it raises `PgQueryError` with a descriptive `message`

### Requirement: FingerprintResult type

The module SHALL provide a `FingerprintResult` named tuple with two fields:

- `fingerprint: int` — the uint64 numeric hash
- `hex: str` — the hexadecimal string representation of the fingerprint

#### Scenario: Named tuple unpacking

- **WHEN** user code runs `fp, hex_str = fingerprint("SELECT 1")`
- **THEN** `fp` is an `int` and `hex_str` is a `str`

#### Scenario: Named field access

- **WHEN** user code runs `result = fingerprint("SELECT 1")`
- **THEN** `result.fingerprint` is an `int` and `result.hex` is a `str`

______________________________________________________________________

## split

### Requirement: Split function

The module SHALL provide a `split(sql: str, *, method: Literal["scanner", "parser"] = "parser") -> list[str]` function
that splits a multi-statement SQL string into individual statement strings. The `method` parameter SHALL select which
libpg_query C function to call:

- `"parser"` (default) -> `pg_query_split_with_parser`
- `"scanner"` -> `pg_query_split_with_scanner`

The function SHALL use byte offsets from the C result to slice the UTF-8 encoded input and decode each slice back to a
Python string.

The C result is freed via `pg_query_free_split_result`.

#### Scenario: Single statement

- **WHEN** `split` is called with `"SELECT 1"`
- **THEN** it returns `["SELECT 1"]`

#### Scenario: Two statements separated by semicolon

- **WHEN** `split` is called with `"SELECT 1; SELECT 2"`
- **THEN** it returns a list of two strings, one for each statement

#### Scenario: Multiple statements with whitespace and comments

- **WHEN** `split` is called with `"SELECT 1;\n\n-- comment\nSELECT 2"`
- **THEN** it returns a list of two strings where the second string includes the leading whitespace and comment as
  returned by the byte range

#### Scenario: Empty semicolons are skipped

- **WHEN** `split` is called with `"SELECT 1;;; SELECT 2"`
- **THEN** it returns a list of two strings (bare semicolons without keywords are not counted as statements)

#### Scenario: Semicolons inside parentheses are not split points

- **WHEN** `split` is called with a statement containing semicolons inside parenthesized expressions (e.g.,
  `CREATE RULE` with multiple sub-statements)
- **THEN** it returns the entire statement as a single entry, not split at the inner semicolons

#### Scenario: Empty string

- **WHEN** `split` is called with `""`
- **THEN** it returns an empty list `[]`

#### Scenario: Invalid SQL raises PgQueryError

- **WHEN** `split` is called with SQL that causes a scanner error
- **THEN** it raises `PgQueryError` with a descriptive `message`

#### Scenario: Default method is parser

- **WHEN** `split` is called without a `method` argument
- **THEN** it behaves identically to `split(sql, method="parser")`

#### Scenario: Parser method with multi-byte characters

- **WHEN** `split` is called with `"SELECT '日本語'; SELECT 1"` and `method="parser"`
- **THEN** both statements are correctly extracted without corruption or offset errors

#### Scenario: Invalid method raises ValueError

- **WHEN** `split` is called with a `method` value that is not `"scanner"` or `"parser"`
- **THEN** it raises `ValueError`

### Requirement: Byte-based slicing for multi-byte characters

The function SHALL encode the input as UTF-8 bytes, use the C result's byte offsets (`stmt_location`, `stmt_len`) to
slice the byte string, and decode each slice back to `str`. This ensures correct results for inputs containing
multi-byte UTF-8 characters.

#### Scenario: Input with multi-byte characters

- **WHEN** `split` is called with SQL containing multi-byte UTF-8 characters (e.g., `"SELECT '日本語'; SELECT 1"`)
- **THEN** both statements are correctly extracted without corruption or offset errors

### Requirement: Native binding for pg_query_split_with_parser

The native bindings module SHALL declare `pg_query_split_with_parser` with argtypes `[c_char_p]` and restype
`PgQuerySplitResult`, matching the existing `pg_query_split_with_scanner` declaration. The result SHALL be freed with
the same `pg_query_free_split_result` function.

#### Scenario: Parser split binding is callable

- **WHEN** `lib.pg_query_split_with_parser` is called with a valid UTF-8 encoded SQL byte string
- **THEN** it returns a `PgQuerySplitResult` struct with statement locations and lengths

______________________________________________________________________

## scan

### Requirement: Scan function

The module SHALL provide a `scan(sql: str) -> ScanResult` function that tokenizes a SQL string by calling libpg_query's
`pg_query_scan` C function and deserializing the binary output into a protobuf `ScanResult` message containing a list of
`ScanToken` objects.

The C result is freed via `pg_query_free_scan_result`.

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

- **WHEN** `scan` is called with SQL containing multi-byte UTF-8 characters (e.g., `"SELECT 'cafe'"`)
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
