# plpgsql Specification

## Purpose

Expose libpg_query's `pg_query_parse_plpgsql` C function as a Python API, enabling users to parse PL/pgSQL function
bodies into structured JSON representations.

## Requirements

### Requirement: parse_plpgsql function

The module SHALL provide a `parse_plpgsql(sql: str) -> list[dict[str, Any]]` function that parses a
`CREATE FUNCTION ... LANGUAGE plpgsql` statement by calling libpg_query's `pg_query_parse_plpgsql` C function and
deserializing the JSON result into Python objects.

#### Scenario: Simple PL/pgSQL function

- **WHEN** `parse_plpgsql` is called with a valid `CREATE FUNCTION ... LANGUAGE plpgsql` statement
- **THEN** it returns a list containing at least one dictionary with a `"PLpgSQL_function"` key

#### Scenario: Function with variable declarations

- **WHEN** `parse_plpgsql` is called with a function containing a `DECLARE` block
- **THEN** the result includes `"datums"` entries describing the declared variables

#### Scenario: Function with control flow

- **WHEN** `parse_plpgsql` is called with a function containing `IF/ELSE` or `LOOP` constructs
- **THEN** the result includes corresponding statement nodes (e.g., `"PLpgSQL_stmt_if"`, `"PLpgSQL_stmt_while"`)

#### Scenario: Function with SQL statements

- **WHEN** `parse_plpgsql` is called with a function containing SQL statements like `SELECT INTO`
- **THEN** the result includes the function action body with the SQL operations

#### Scenario: Invalid PL/pgSQL raises PgQueryError

- **WHEN** `parse_plpgsql` is called with syntactically invalid PL/pgSQL
- **THEN** it raises `PgQueryError` with a descriptive `message`

#### Scenario: Non-plpgsql function returns trivial result

- **WHEN** `parse_plpgsql` is called with a `LANGUAGE sql` function
- **THEN** it returns a near-empty structure (libpg_query does not reject non-plpgsql input; users should only pass
  `LANGUAGE plpgsql` functions)

#### Scenario: CREATE OR REPLACE

- **WHEN** `parse_plpgsql` is called with `CREATE OR REPLACE FUNCTION ... LANGUAGE plpgsql`
- **THEN** it parses successfully and returns the same structure as a plain `CREATE FUNCTION`

### Requirement: JSON deserialization

The function SHALL deserialize the JSON string returned by the C function into native Python objects
(`list[dict[str, Any]]`) using `json.loads`, rather than returning the raw JSON string.

#### Scenario: Return type is Python list

- **WHEN** `parse_plpgsql` is called with valid input
- **THEN** the return value is a Python `list` of `dict` objects, not a string

### Requirement: Result memory is always freed

The C result struct returned by `pg_query_parse_plpgsql` SHALL always be freed via `pg_query_free_plpgsql_parse_result`,
regardless of whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `parse_plpgsql` is called with valid PL/pgSQL and returns successfully
- **THEN** the C result struct is freed after extracting the JSON string

#### Scenario: Memory freed on error

- **WHEN** `parse_plpgsql` is called with invalid PL/pgSQL and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

### Requirement: Public API export

The `parse_plpgsql` function SHALL be importable directly from the `postgast` package (i.e.,
`from postgast import parse_plpgsql`).

#### Scenario: Top-level import

- **WHEN** user code runs `from postgast import parse_plpgsql`
- **THEN** the name resolves without error and is callable
