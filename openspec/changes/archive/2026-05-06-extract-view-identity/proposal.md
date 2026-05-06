## Why

`helpers.py` has `extract_function_identity` and `extract_trigger_identity` for pinpointing CREATE FUNCTION and CREATE
TRIGGER statements, but no equivalents for views, indexes, sequences, or schemas. Tools that manage schema migrations
need the same capability for any DDL object that has a qualified name.

## What Changes

- Add `ViewIdentity` NamedTuple (`schema`, `name`) and `extract_view_identity` function for `ViewStmt`.
- Add `IndexIdentity` NamedTuple (`schema`, `name`) and `extract_index_identity` function for `IndexStmt`.
- Add `SequenceIdentity` NamedTuple (`schema`, `name`) and `extract_sequence_identity` function for `CreateSeqStmt`.
- Add `SchemaIdentity` NamedTuple (`name`) and `extract_schema_identity` function for `CreateSchemaStmt`.
- Export all four NamedTuples and four functions from `postgast.__init__`.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `ast-navigation`: Add `ViewIdentity`, `IndexIdentity`, `SequenceIdentity`, `SchemaIdentity` NamedTuples and their
  corresponding `extract_*_identity` functions with public-API export requirements, mirroring the existing
  `FunctionIdentity`/`TriggerIdentity` pattern.

## Impact

- `src/postgast/helpers.py` — four new NamedTuple classes and four new extractor functions
- `src/postgast/__init__.py` — add all four types and functions to imports and `__all__`
- `tests/` — new unit tests for each extractor
- `openspec/specs/ast-navigation/spec.md` — updated via delta spec (no breakage to existing requirements)
