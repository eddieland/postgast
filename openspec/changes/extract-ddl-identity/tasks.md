## 1. NamedTuple types

- [ ] 1.1 Define `FunctionIdentity(schema: str | None, name: str)` as a `typing.NamedTuple` in `helpers.py`
- [ ] 1.2 Define `TriggerIdentity(trigger: str, schema: str | None, table: str)` as a `typing.NamedTuple` in
  `helpers.py`

## 2. Identity extraction functions

- [ ] 2.1 Implement `extract_function_identity(tree) -> FunctionIdentity | None` in `helpers.py` — find first
  `CreateFunctionStmt` with `is_procedure=False`, extract schema and name from `funcname` repeated Node list, return
  `None` for absent schema
- [ ] 2.2 Implement `extract_trigger_identity(tree) -> TriggerIdentity | None` in `helpers.py` — find first
  `CreateTrigStmt`, extract `trigname` and schema/table from `relation` RangeVar, return `None` for absent schema

## 3. Public API exports

- [ ] 3.1 Add `FunctionIdentity`, `TriggerIdentity`, `extract_function_identity`, and `extract_trigger_identity` to
  `__init__.py` re-exports and `__all__`

## 4. Tests

- [ ] 4.1 Test `extract_function_identity`: schema-qualified, unqualified, OR REPLACE, procedure skipped, no match,
  comments before name
- [ ] 4.2 Test `extract_trigger_identity`: schema-qualified table, unqualified table, OR REPLACE, no match
- [ ] 4.3 Test tuple unpacking for both NamedTuples
- [ ] 4.4 Test direct import of new functions and types from `postgast`
