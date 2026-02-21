## MODIFIED Requirements

### Requirement: Split function

The module SHALL provide a `split(sql: str, *, method: Literal["scanner", "parser"] = "scanner") -> list[str]` function
that splits a multi-statement SQL string into individual statement strings. The `method` parameter SHALL select which
libpg_query C function to call:

- `"scanner"` (default) → `pg_query_split_with_scanner`
- `"parser"` → `pg_query_split_with_parser`

The function SHALL use byte offsets from the C result to slice the UTF-8 encoded input and decode each slice back to a
Python string.

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

#### Scenario: Default method is scanner

- **WHEN** `split` is called without a `method` argument
- **THEN** it behaves identically to `split(sql, method="scanner")`

#### Scenario: Parser method splits valid SQL

- **WHEN** `split` is called with `"SELECT 1; SELECT 2"` and `method="parser"`
- **THEN** it returns a list of two strings, one for each statement

#### Scenario: Parser method with multi-byte characters

- **WHEN** `split` is called with `"SELECT '日本語'; SELECT 1"` and `method="parser"`
- **THEN** both statements are correctly extracted without corruption or offset errors

#### Scenario: Parser method rejects invalid SQL

- **WHEN** `split` is called with SQL that contains a parse error and `method="parser"`
- **THEN** it raises `PgQueryError` with a descriptive `message`

#### Scenario: Invalid method raises ValueError

- **WHEN** `split` is called with a `method` value that is not `"scanner"` or `"parser"`
- **THEN** it raises `ValueError`

### Requirement: Result memory is always freed

The C result struct returned by the selected split function (`pg_query_split_with_scanner` or
`pg_query_split_with_parser`) SHALL always be freed via `pg_query_free_split_result`, regardless of whether the call
succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `split` is called with valid SQL and returns successfully
- **THEN** the C result struct is freed after extracting the statement strings

#### Scenario: Memory freed on error

- **WHEN** `split` is called with SQL that causes an error and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

## ADDED Requirements

### Requirement: Native binding for pg_query_split_with_parser

The native bindings module SHALL declare `pg_query_split_with_parser` with argtypes `[c_char_p]` and restype
`PgQuerySplitResult`, matching the existing `pg_query_split_with_scanner` declaration. The result SHALL be freed with
the same `pg_query_free_split_result` function.

#### Scenario: Parser split binding is callable

- **WHEN** `lib.pg_query_split_with_parser` is called with a valid UTF-8 encoded SQL byte string
- **THEN** it returns a `PgQuerySplitResult` struct with statement locations and lengths
