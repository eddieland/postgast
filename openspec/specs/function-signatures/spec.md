# function-signatures Specification

## Purpose

TBD - created by archiving change ctypes-library-loading. Update Purpose after archive.

## Requirements

### Requirement: Core function signatures declared

The module SHALL set argtypes and restype on all public libpg_query functions: pg_query_parse, pg_query_parse_protobuf,
pg_query_normalize, pg_query_fingerprint, pg_query_scan, pg_query_split_with_scanner, pg_query_deparse_protobuf, and
their corresponding pg_query_free\_\* functions.

#### Scenario: Parse function signature

- **WHEN** pg_query_parse is called via ctypes with a bytes argument
- **THEN** it returns a PgQueryParseResult struct

#### Scenario: Free function signature

- **WHEN** a pg_query_free\_\* function is called with its corresponding result struct
- **THEN** it completes without error and the result memory is released
