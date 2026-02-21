## Requirements

### Requirement: Fingerprint function

The module SHALL provide a `fingerprint(query: str) -> FingerprintResult` function that computes a structural
fingerprint of a SQL query by calling libpg_query's `pg_query_fingerprint` C function. The fingerprint identifies
structurally equivalent queries regardless of literal values.

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

### Requirement: Result memory is always freed

The C result struct returned by `pg_query_fingerprint` SHALL always be freed via `pg_query_free_fingerprint_result`,
regardless of whether the call succeeded or raised an error.

#### Scenario: Memory freed on success

- **WHEN** `fingerprint` is called with valid SQL and returns successfully
- **THEN** the C result struct is freed after extracting the fingerprint values

#### Scenario: Memory freed on error

- **WHEN** `fingerprint` is called with invalid SQL and raises `PgQueryError`
- **THEN** the C result struct is freed before the exception propagates

### Requirement: Public API export

The `fingerprint` function and `FingerprintResult` type SHALL be importable directly from the `postgast` package (i.e.,
`from postgast import fingerprint, FingerprintResult`).

#### Scenario: Top-level import

- **WHEN** user code runs `from postgast import fingerprint, FingerprintResult`
- **THEN** both names resolve without error
