# split Specification

## Purpose

Public function to split a multi-statement SQL string into individual statements using libpg_query's scanner-based
splitter.

## Requirements

### Requirement: Split function

The module SHALL provide a `split(sql: str) -> list[str]` function that splits a multi-statement SQL string into
individual statement strings by calling libpg_query's `pg_query_split_with_scanner` C function. The function SHALL use
byte offsets from the C result to slice the UTF-8 encoded input and decode each slice back to a Python string.

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

### Requirement: Byte-based slicing for multi-byte characters

The function SHALL encode the input as UTF-8 bytes, use the C result's byte offsets (`stmt_location`, `stmt_len`) to
slice the byte string, and decode each slice back to `str`. This ensures correct results for inputs containing
multi-byte UTF-8 characters.

#### Scenario: Input with multi-byte characters

- **WHEN** `split` is called with SQL containing multi-byte UTF-8 characters (e.g., `"SELECT '日本語'; SELECT 1"`)
- **THEN** both statements are correctly extracted without corruption or offset errors

### Requirement: Result memory is always freed

The C result struct returned by `pg_query_split_with_scanner` SHALL always be freed via `pg_query_free_split_result`,
regardless of whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `split` is called with valid SQL and returns successfully
- **THEN** the C result struct is freed after extracting the statement strings

#### Scenario: Memory freed on error

- **WHEN** `split` is called with SQL that causes a scanner error and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

### Requirement: Public API export

The `split` function SHALL be importable directly from the `postgast` package (i.e., `from postgast import split`).

#### Scenario: Top-level import

- **WHEN** user code runs `from postgast import split`
- **THEN** the name resolves without error and is callable
