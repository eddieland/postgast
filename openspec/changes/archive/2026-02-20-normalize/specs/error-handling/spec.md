## ADDED Requirements

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
non-null, the helper SHALL extract the error fields, free the C result, and raise `PgQueryError`.

#### Scenario: Non-null error pointer raises exception

- **WHEN** a C function returns a result with a non-null error pointer
- **THEN** the helper raises `PgQueryError` with the error fields populated and the C result memory is freed

#### Scenario: Null error pointer does not raise

- **WHEN** a C function returns a result with a null error pointer
- **THEN** the helper returns without raising and the result remains available for value extraction
