## Why

Users who parse SQL with postgast get back a protobuf AST and must manually walk the tree (via `walk()` or `Visitor`) to
answer common questions like "which tables does this query reference?" or "what columns are selected?". A small set of
ready-made helper functions would cover the most frequent use cases and make postgast immediately useful for SQL
analysis without requiring protobuf knowledge.

## What Changes

- Add `find_nodes(tree, node_type)` — generic iterator that yields all protobuf messages of a given type from a parse
  tree. The building block for all specific extractors and for ad-hoc queries by users.
- Add `extract_tables(tree)` — returns all table names referenced in a parse tree (via `RangeVar` nodes), including
  schema-qualified names.
- Add `extract_columns(tree)` — returns column references found in a parse tree (via `ColumnRef` nodes).
- Add `extract_functions(tree)` — returns function call names found in a parse tree (via `FuncCall` nodes).
- Add a new `helpers.py` module containing the implementations.
- Re-export all helpers from `__init__.py` for a clean public API.

## Capabilities

### New Capabilities

- `ast-helpers`: Convenience functions that extract common structural information (tables, columns, functions) from a
  parsed SQL AST.

### Modified Capabilities

*(none — the existing `walk`/`Visitor` API is unchanged; helpers build on top of it)*

## Impact

- **New file**: `src/postgast/helpers.py`
- **Modified file**: `src/postgast/__init__.py` (new re-exports)
- **New tests**: `tests/postgast/test_helpers.py`
- **Public API**: Four new functions added to the `postgast` namespace
- **Dependencies**: No new dependencies — uses existing `walk` and protobuf types
