## 1. Implementation

- [x] 1.1 Add `ViewIdentity` NamedTuple to `src/postgast/helpers.py` (fields: `schema: str | None`, `name: str`)
- [x] 1.2 Add `extract_view_identity(tree: Message) -> ViewIdentity | None` to `src/postgast/helpers.py`
- [x] 1.3 Add `IndexIdentity` NamedTuple to `src/postgast/helpers.py` (fields: `schema: str | None`, `name: str`)
- [x] 1.4 Add `extract_index_identity(tree: Message) -> IndexIdentity | None` to `src/postgast/helpers.py`
- [x] 1.5 Add `SequenceIdentity` NamedTuple to `src/postgast/helpers.py` (fields: `schema: str | None`, `name: str`)
- [x] 1.6 Add `extract_sequence_identity(tree: Message) -> SequenceIdentity | None` to `src/postgast/helpers.py`
- [x] 1.7 Add `SchemaIdentity` NamedTuple to `src/postgast/helpers.py` (field: `name: str`)
- [x] 1.8 Add `extract_schema_identity(tree: Message) -> SchemaIdentity | None` to `src/postgast/helpers.py`
- [x] 1.9 Export all four NamedTuples and four functions from `src/postgast/__init__.py` (imports + `__all__`)

## 2. Tests

- [x] 2.1 Add unit tests for `extract_view_identity`: schema-qualified, unqualified, `CREATE OR REPLACE VIEW`, no view
  returns `None`, multiple views returns first
- [x] 2.2 Add unit tests for `extract_index_identity`: schema-qualified, unqualified, no index returns `None`
- [x] 2.3 Add unit tests for `extract_sequence_identity`: schema-qualified, unqualified, no sequence returns `None`
- [x] 2.4 Add unit tests for `extract_schema_identity`: plain schema, no schema returns `None`
- [x] 2.5 Add unit test for direct import of all new symbols from `postgast`
