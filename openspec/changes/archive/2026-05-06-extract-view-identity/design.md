## Context

`helpers.py` already implements `extract_function_identity` (for `CreateFunctionStmt`) and `extract_trigger_identity`
(for `CreateTrigStmt`) as thin wrappers around `find_nodes`. This change adds the same pattern for the four remaining
DDL statement types that carry a qualified name: `ViewStmt`, `IndexStmt`, `CreateSeqStmt`, and `CreateSchemaStmt`. All
four node types are already imported in `helpers.py`.

## Goals / Non-Goals

**Goals:**

- Add `ViewIdentity(schema, name)`, `IndexIdentity(schema, name)`, `SequenceIdentity(schema, name)`, and
  `SchemaIdentity(name)` NamedTuples to `helpers.py`.
- Add `extract_view_identity`, `extract_index_identity`, `extract_sequence_identity`, and `extract_schema_identity`
  functions that each return the corresponding NamedTuple or `None`.
- Export all eight new symbols from `postgast.__init__`.

**Non-Goals:**

- Distinguishing regular views from materialized views.
- Extracting the view body, index predicate, sequence options, or schema body.
- Handling `ALTER` or `DROP` variants — those are covered by `to_drop`.

## Decisions

### Field sources per node type

| Type               | NamedTuple         | Schema field          | Name field         |
| ------------------ | ------------------ | --------------------- | ------------------ |
| `ViewStmt`         | `ViewIdentity`     | `view.schemaname`     | `view.relname`     |
| `IndexStmt`        | `IndexIdentity`    | `relation.schemaname` | `idxname`          |
| `CreateSeqStmt`    | `SequenceIdentity` | `sequence.schemaname` | `sequence.relname` |
| `CreateSchemaStmt` | `SchemaIdentity`   | —                     | `schemaname`       |

`IndexStmt` has no dedicated schema field on the index itself; PostgreSQL places an index in the same schema as its
table, so `relation.schemaname` is the correct source (same logic used by `_drop_index`).

`SchemaIdentity` has no `schema` field because schemas are top-level namespace objects — there is no parent schema.

### Return `None` for trees without a matching node

Matches the existing contract of `extract_function_identity` and `extract_trigger_identity`.

### `schema: str | None` normalized from empty string

`ViewStmt.view.schemaname` (and the other `RangeVar`-style fields) returns `""` when unqualified, not `None`. Each
extractor SHALL return `None` for `schema` when the raw field is falsy (`""` or unset), matching how
`extract_trigger_identity` already handles `node.relation.schemaname or None`.

## Risks / Trade-offs

- [Future fields] `IndexIdentity` omits `table` even though `IndexStmt` knows which table the index belongs to. Callers
  that need the table name can read `IndexStmt.relation` directly via `find_nodes`. Keeping the NamedTuple minimal stays
  consistent with `ViewIdentity` and `SequenceIdentity`.
