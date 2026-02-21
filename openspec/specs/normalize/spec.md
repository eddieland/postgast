# normalize Specification

## Purpose

Public `normalize()` function that replaces SQL literal constants with parameter placeholders via libpg_query.

## Requirements

### Requirement: Normalize function

The module SHALL provide a `normalize(query: str) -> str` function that replaces literal constants in a SQL query with
parameter placeholders (`$1`, `$2`, ...) by calling libpg_query's `pg_query_normalize` C function.

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

### Requirement: Result memory is always freed

The C result struct returned by `pg_query_normalize` SHALL always be freed via `pg_query_free_normalize_result`,
regardless of whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `normalize` is called with valid SQL and returns successfully
- **THEN** the C result struct is freed after extracting the normalized query

#### Scenario: Memory freed on error

- **WHEN** `normalize` is called with invalid SQL and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

### Requirement: Public API export

The `normalize` function and `PgQueryError` exception SHALL be importable directly from the `postgast` package (i.e.,
`from postgast import normalize, PgQueryError`).

#### Scenario: Top-level import

- **WHEN** user code runs `from postgast import normalize, PgQueryError`
- **THEN** both names resolve without error
