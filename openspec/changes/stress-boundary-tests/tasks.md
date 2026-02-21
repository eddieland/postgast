## 1. Setup

- [ ] 1.1 Register `stress` marker in `pyproject.toml` under `[tool.pytest.ini_options] markers`

## 2. Stress tests (`tests/postgast/test_stress.py`)

- [ ] 2.1 Create `test_stress.py` with `pytestmark = pytest.mark.stress` and shared helpers for generating large SQL
  (wide SELECT, many statements, nested parens, nested subqueries, many JOINs, many CASE branches, large IN lists)
- [ ] 2.2 Add large-input tests: parse, normalize, fingerprint, split, scan with 1,000-column SELECT and 1,000-statement
  input
- [ ] 2.3 Add deparse large-input test: parse a 1,000-column SELECT then deparse the result
- [ ] 2.4 Add deep-nesting tests: parse, normalize, fingerprint, split, scan with 500-level nested parens
- [ ] 2.5 Add deep-subquery test: parse with 100-level nested subqueries
- [ ] 2.6 Add wide-query tests: parse with 50-table JOIN, parse with 500-branch CASE, normalize with 1,000-value IN list

## 3. Boundary tests (`tests/postgast/test_boundary.py`)

- [ ] 3.1 Create `test_boundary.py` with parametrized null-byte tests for parse, normalize, fingerprint, split, scan
- [ ] 3.2 Add control-character tests: parametrize parse and scan with `\t`, `\v`, `\f`, `\b`, `\a` inputs
- [ ] 3.3 Add Unicode edge-case tests: parse with emoji string literals, zero-width characters in identifiers, scan with
  non-BMP codepoints, split with multi-byte Unicode
- [ ] 3.4 Add malformed-SQL tests: parse with unterminated string, unterminated block comment, mismatched parens,
  partial statements; normalize and fingerprint with malformed SQL; split with unterminated construct; scan with garbage
  bytes
- [ ] 3.5 Add long-token tests: parse and scan with 100,000-character quoted identifier and string literal
- [ ] 3.6 Add error-resilience tests: parse succeeds after prior error, all operations succeed after prior errors,
  100-cycle error-success loop with no state leakage

## 4. Verify

- [ ] 4.1 Run full test suite (`make test`) and confirm all new tests pass
- [ ] 4.2 Run `pytest -m "not stress"` and confirm stress tests are excluded while boundary tests still run
- [ ] 4.3 Run `make lint` and confirm no type or lint errors
