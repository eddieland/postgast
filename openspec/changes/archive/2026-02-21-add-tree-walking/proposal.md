## Why

Working with postgast parse trees requires manually recursing through deeply nested protobuf messages, checking
`WhichOneof('node')` at every `Node` union, and knowing which fields on each of the 130+ node types contain child nodes.
This makes even simple tasks — collecting all table references, rewriting column names, finding subqueries — tedious and
error-prone. A tree walking and visitor API lets users traverse and inspect parse trees without needing to understand
the full protobuf structure.

## What Changes

- Add a generic depth-first tree walker that recursively visits every node in a parse tree, yielding each node without
  requiring callers to know the protobuf schema
- Add a visitor base class with per-node-type dispatch (e.g., `visit_SelectStmt`, `visit_ColumnRef`) so users can react
  to specific node types while the framework handles traversal
- Provide both iteration-based (walk) and callback-based (visitor) interfaces to support different usage patterns

## Capabilities

### New Capabilities

- `tree-walking`: Generic parse tree traversal (walk/iterate all nodes) and visitor pattern with per-node-type dispatch

### Modified Capabilities

None — this is purely additive and does not change any existing capability requirements.

## Impact

- **New files**: `src/postgast/_walk.py` (or similar) containing walk and visitor implementations
- **Modified files**: `src/postgast/__init__.py` to export the new public API
- **New tests**: `tests/postgast/test_walk.py`
- **Dependencies**: No new dependencies — uses protobuf message introspection (`DESCRIPTOR`, `ListFields`, `WhichOneof`)
  which is already available
- **API surface**: Adds new public names to `postgast` (e.g., `walk`, `Visitor` or similar)
