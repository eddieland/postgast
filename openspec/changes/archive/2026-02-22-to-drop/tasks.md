## 1. Core Implementation

- [x] 1.1 Add `to_drop()` function to `src/postgast/helpers.py` with internal dispatch for CreateFunctionStmt,
  CreateTrigStmt, and ViewStmt
- [x] 1.2 Export `to_drop` from `src/postgast/__init__.py` and add to `__all__`

## 2. Tests

- [x] 2.1 Add tests for DROP FUNCTION generation (named params, no-arg, OUT exclusion, VARIADIC, unqualified, quoted
  identifiers, OR REPLACE)
- [x] 2.2 Add tests for DROP PROCEDURE generation
- [x] 2.3 Add tests for DROP TRIGGER generation (schema-qualified and unqualified)
- [x] 2.4 Add tests for DROP VIEW generation (schema-qualified, unqualified, OR REPLACE)
- [x] 2.5 Add tests for error cases (unsupported statement, multi-statement, invalid SQL)

## 3. Validation

- [x] 3.1 Run `make lint` and fix any type-check or formatting issues
- [x] 3.2 Run `make test` and confirm all tests pass
