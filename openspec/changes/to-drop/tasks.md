## 1. Core Implementation

- [ ] 1.1 Add `to_drop()` function to `src/postgast/helpers.py` with internal dispatch for CreateFunctionStmt,
  CreateTrigStmt, and ViewStmt
- [ ] 1.2 Export `to_drop` from `src/postgast/__init__.py` and add to `__all__`

## 2. Tests

- [ ] 2.1 Add tests for DROP FUNCTION generation (named params, no-arg, OUT exclusion, VARIADIC, unqualified, quoted
  identifiers, OR REPLACE)
- [ ] 2.2 Add tests for DROP PROCEDURE generation
- [ ] 2.3 Add tests for DROP TRIGGER generation (schema-qualified and unqualified)
- [ ] 2.4 Add tests for DROP VIEW generation (schema-qualified, unqualified, OR REPLACE)
- [ ] 2.5 Add tests for error cases (unsupported statement, multi-statement, invalid SQL)

## 3. Validation

- [ ] 3.1 Run `make lint` and fix any type-check or formatting issues
- [ ] 3.2 Run `make test` and confirm all tests pass
