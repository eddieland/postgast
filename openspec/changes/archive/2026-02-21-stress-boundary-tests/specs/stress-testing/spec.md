## ADDED Requirements

### Requirement: Large SQL input handling

Every core operation (parse, deparse, normalize, fingerprint, split, scan) SHALL handle SQL inputs up to 10 MB without
crashing. The operation SHALL either return a valid result or raise `PgQueryError`.

#### Scenario: Parse a large SELECT with many columns

- **WHEN** `parse()` is called with a SELECT containing 1,000 column expressions
- **THEN** it returns a `ParseResult` with one statement, or raises `PgQueryError`

#### Scenario: Normalize a large query

- **WHEN** `normalize()` is called with a SELECT containing 1,000 literal values
- **THEN** it returns a normalized string with placeholders, or raises `PgQueryError`

#### Scenario: Fingerprint a large query

- **WHEN** `fingerprint()` is called with a SELECT containing 1,000 column expressions
- **THEN** it returns a `FingerprintResult`, or raises `PgQueryError`

#### Scenario: Split a string with many statements

- **WHEN** `split()` is called with a string containing 1,000 semicolon-separated statements
- **THEN** it returns a list of 1,000 statements, or raises `PgQueryError`

#### Scenario: Scan a large query

- **WHEN** `scan()` is called with a SELECT containing 1,000 column expressions
- **THEN** it returns a `ScanResult` with tokens, or raises `PgQueryError`

#### Scenario: Deparse a large parse result

- **WHEN** a large SELECT with 1,000 columns is parsed and the resulting protobuf is passed to `deparse()`
- **THEN** it returns a SQL string, or raises `PgQueryError`

### Requirement: Deeply nested expression handling

Every core operation SHALL handle deeply nested SQL expressions (up to 500 levels) without crashing. The operation SHALL
either return a valid result or raise `PgQueryError`.

#### Scenario: Parse deeply nested parenthesized expressions

- **WHEN** `parse()` is called with `SELECT` followed by 500 levels of nested parentheses around a literal (e.g.,
  `SELECT ((((...1...))))`)
- **THEN** it returns a `ParseResult` or raises `PgQueryError`

#### Scenario: Parse deeply nested subqueries

- **WHEN** `parse()` is called with 100 levels of nested subqueries (e.g.,
  `SELECT * FROM (SELECT * FROM (... SELECT 1 ...))`)
- **THEN** it returns a `ParseResult` or raises `PgQueryError`

#### Scenario: Normalize deeply nested expression

- **WHEN** `normalize()` is called with 500 levels of nested parenthesized expressions
- **THEN** it returns a string or raises `PgQueryError`

#### Scenario: Fingerprint deeply nested expression

- **WHEN** `fingerprint()` is called with 500 levels of nested parenthesized expressions
- **THEN** it returns a `FingerprintResult` or raises `PgQueryError`

#### Scenario: Split input containing deeply nested query

- **WHEN** `split()` is called with a string containing a deeply nested query
- **THEN** it returns a list or raises `PgQueryError`

#### Scenario: Scan deeply nested expression

- **WHEN** `scan()` is called with 500 levels of nested parenthesized expressions
- **THEN** it returns a `ScanResult` or raises `PgQueryError`

### Requirement: Wide query handling

Every core operation SHALL handle queries with a large number of JOINs, parameters, or CASE branches without crashing.

#### Scenario: Parse a query with many JOINs

- **WHEN** `parse()` is called with a SELECT joining 50 tables
- **THEN** it returns a `ParseResult` or raises `PgQueryError`

#### Scenario: Parse a query with many CASE branches

- **WHEN** `parse()` is called with a CASE expression containing 500 WHEN clauses
- **THEN** it returns a `ParseResult` or raises `PgQueryError`

#### Scenario: Normalize a query with many parameters

- **WHEN** `normalize()` is called with a query containing 1,000 literal values in an IN list
- **THEN** it returns a normalized string or raises `PgQueryError`

### Requirement: Stress tests are marked for selective execution

All stress tests SHALL be marked with `@pytest.mark.stress` so they can be excluded from fast CI runs via
`pytest -m "not stress"`.

#### Scenario: Stress marker is registered

- **WHEN** pytest collects tests
- **THEN** the `stress` marker is registered in `pyproject.toml` and produces no unknown-marker warnings

#### Scenario: Stress tests are skippable

- **WHEN** pytest is invoked with `-m "not stress"`
- **THEN** no tests from `test_stress.py` are collected, and all tests from `test_boundary.py` are still collected
