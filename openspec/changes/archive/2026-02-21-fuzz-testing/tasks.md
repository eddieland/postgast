## 1. Dependencies and Configuration

- [x] 1.1 Add `hypothesis` to the dev dependency group in `pyproject.toml`
- [x] 1.2 Register the `fuzz` pytest mark in `pyproject.toml` under `[tool.pytest.ini_options]` markers
- [x] 1.3 Add `-m "not fuzz"` to the default pytest invocation in the `test` and `coverage` Makefile targets so fuzz
  tests are excluded by default
- [x] 1.4 Add a `fuzz` target to the Makefile: `uv run pytest -m fuzz`
- [x] 1.5 Add `.hypothesis/` to `.gitignore` if not already present

## 2. Input Strategies

- [x] 2.1 Create `tests/postgast/test_fuzz.py` with Hypothesis imports and a configurable `max_examples` setting that
  reads from the `HYPOTHESIS_MAX_EXAMPLES` env var (default 1000)
- [x] 2.2 Implement the SQL-biased input strategy (`sql_input`): `st.one_of` compositing arbitrary text, binary-decoded
  strings, SQL fragment generator (keywords, operators, punctuation, identifiers, literals), and edge cases (empty
  string, null bytes, long strings, nested parens)

## 3. String-Accepting Function Fuzz Tests

- [x] 3.1 Add `test_parse_does_not_crash` — fuzz `parse` with the `sql_input` strategy, assert returns `ParseResult` or
  raises `PgQueryError`
- [x] 3.2 Add `test_normalize_does_not_crash` — fuzz `normalize` with the `sql_input` strategy
- [x] 3.3 Add `test_fingerprint_does_not_crash` — fuzz `fingerprint` with the `sql_input` strategy
- [x] 3.4 Add `test_scan_does_not_crash` — fuzz `scan` with the `sql_input` strategy
- [x] 3.5 Add `test_split_does_not_crash` — fuzz `split` with the `sql_input` strategy

## 4. Deparse Fuzz Tests

- [x] 4.1 Add `test_deparse_roundtrip_does_not_crash` — parse valid SQL from a pool of statements, then deparse, assert
  no crash
- [x] 4.2 Add `test_deparse_mutated_tree_does_not_crash` — parse valid SQL, mutate the `ParseResult` (clear fields,
  change values), then deparse, assert returns `str` or raises `PgQueryError`

## 5. Verification

- [x] 5.1 Run `make fuzz` and verify all fuzz tests pass
- [x] 5.2 Run `make test` and verify fuzz tests are excluded
- [x] 5.3 Run `make lint` and verify no type or lint errors
