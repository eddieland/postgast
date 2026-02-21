## ADDED Requirements

### Requirement: Null byte handling

Every core operation (parse, deparse, normalize, fingerprint, split, scan) SHALL handle input containing embedded null
bytes (`\x00`) without crashing. The operation SHALL either return a result (possibly truncated at the null byte) or
raise `PgQueryError`.

#### Scenario: Parse SQL with embedded null byte

- **WHEN** `parse()` is called with `"SELECT\x001"`
- **THEN** it returns a `ParseResult` or raises `PgQueryError` — no crash

#### Scenario: Normalize SQL with embedded null byte

- **WHEN** `normalize()` is called with `"SELECT\x001"`
- **THEN** it returns a string or raises `PgQueryError` — no crash

#### Scenario: Fingerprint SQL with embedded null byte

- **WHEN** `fingerprint()` is called with `"SELECT\x001"`
- **THEN** it returns a `FingerprintResult` or raises `PgQueryError` — no crash

#### Scenario: Split SQL with embedded null byte

- **WHEN** `split()` is called with `"SELECT 1;\x00SELECT 2"`
- **THEN** it returns a list or raises `PgQueryError` — no crash

#### Scenario: Scan SQL with embedded null byte

- **WHEN** `scan()` is called with `"SELECT\x001"`
- **THEN** it returns a `ScanResult` or raises `PgQueryError` — no crash

### Requirement: Control character handling

Every core operation SHALL handle input containing ASCII control characters (tabs, vertical tabs, form feeds, backspace,
bell) without crashing.

#### Scenario: Parse SQL with control characters

- **WHEN** `parse()` is called with SQL containing `\t`, `\v`, `\f`, `\b`, or `\a` characters
- **THEN** it returns a `ParseResult` or raises `PgQueryError` — no crash

#### Scenario: Scan SQL with control characters

- **WHEN** `scan()` is called with SQL containing control characters
- **THEN** it returns a `ScanResult` or raises `PgQueryError` — no crash

### Requirement: Unicode edge case handling

Every core operation SHALL handle input containing non-BMP Unicode characters (emoji, CJK supplementary), zero-width
characters, and Unicode edge cases without crashing.

#### Scenario: Parse SQL with emoji in string literal

- **WHEN** `parse()` is called with `SELECT '🎉🚀'`
- **THEN** it returns a `ParseResult` with one statement

#### Scenario: Parse SQL with zero-width characters in identifier

- **WHEN** `parse()` is called with SQL containing zero-width spaces (`\u200b`) or zero-width joiners (`\u200d`) in
  identifiers
- **THEN** it returns a `ParseResult` or raises `PgQueryError` — no crash

#### Scenario: Scan SQL with non-BMP codepoints

- **WHEN** `scan()` is called with SQL containing emoji or CJK supplementary characters
- **THEN** it returns a `ScanResult` or raises `PgQueryError` — no crash

#### Scenario: Split SQL with multi-byte Unicode

- **WHEN** `split()` is called with `"SELECT '🎉'; SELECT '日本語'"`
- **THEN** it returns a list of two statements or raises `PgQueryError` — no crash

### Requirement: Malformed SQL error handling

Every core operation that accepts raw SQL SHALL raise `PgQueryError` (not crash) when given systematically malformed
inputs: unterminated strings, unterminated comments, mismatched parentheses, partial statements, and garbage bytes.

#### Scenario: Parse unterminated string literal

- **WHEN** `parse()` is called with `"SELECT 'unterminated"`
- **THEN** it raises `PgQueryError`

#### Scenario: Parse unterminated block comment

- **WHEN** `parse()` is called with `"SELECT /* never closed"`
- **THEN** it raises `PgQueryError`

#### Scenario: Parse mismatched parentheses

- **WHEN** `parse()` is called with `"SELECT ((1)"`
- **THEN** it raises `PgQueryError`

#### Scenario: Parse partial statement

- **WHEN** `parse()` is called with `"SELECT"`, `"INSERT INTO"`, or `"CREATE TABLE"`
- **THEN** it raises `PgQueryError`

#### Scenario: Normalize malformed SQL

- **WHEN** `normalize()` is called with malformed SQL (unterminated strings, mismatched parens)
- **THEN** it raises `PgQueryError`

#### Scenario: Fingerprint malformed SQL

- **WHEN** `fingerprint()` is called with malformed SQL
- **THEN** it raises `PgQueryError`

#### Scenario: Split unterminated construct

- **WHEN** `split()` is called with `"SELECT 'unterminated; SELECT 2"`
- **THEN** it raises `PgQueryError`

#### Scenario: Scan garbage bytes

- **WHEN** `scan()` is called with random bytes decoded as a string
- **THEN** it returns a `ScanResult` (possibly with error tokens) or raises `PgQueryError` — no crash

### Requirement: Extremely long identifiers and string literals

Every core operation SHALL handle SQL containing identifiers or string literals at extreme lengths (100 KB+) without
crashing.

#### Scenario: Parse SQL with a very long identifier

- **WHEN** `parse()` is called with `SELECT` followed by a quoted identifier of 100,000 characters
- **THEN** it returns a `ParseResult` or raises `PgQueryError` — no crash

#### Scenario: Parse SQL with a very long string literal

- **WHEN** `parse()` is called with `SELECT` followed by a string literal of 100,000 characters
- **THEN** it returns a `ParseResult` or raises `PgQueryError` — no crash

#### Scenario: Scan SQL with a very long token

- **WHEN** `scan()` is called with a string literal of 100,000 characters
- **THEN** it returns a `ScanResult` or raises `PgQueryError` — no crash

### Requirement: Error resilience across sequential calls

The library SHALL not leak state between calls. After a call that raises `PgQueryError`, the next call with valid SQL
SHALL succeed normally.

#### Scenario: Parse succeeds after prior parse error

- **WHEN** `parse()` is called with invalid SQL and raises `PgQueryError`, then `parse()` is called with `"SELECT 1"`
- **THEN** the second call returns a valid `ParseResult` with one statement

#### Scenario: All operations succeed after prior errors

- **WHEN** each of parse, normalize, fingerprint, split, and scan is called with invalid SQL (each raising
  `PgQueryError`), then each is called again with valid SQL
- **THEN** every second call succeeds with a valid result

#### Scenario: No state leakage across many error-success cycles

- **WHEN** 100 cycles of (invalid SQL → `PgQueryError`, valid SQL → success) are executed against `parse()`
- **THEN** every valid-SQL call returns a correct `ParseResult`
