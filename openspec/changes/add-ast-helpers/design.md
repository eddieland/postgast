## Context

postgast currently exposes low-level tree traversal via `walk()` (generator) and `Visitor` (class-based dispatch). Both
work directly with protobuf messages, requiring users to know protobuf field names like `RangeVar.relname`,
`ColumnRef.fields`, and `FuncCall.funcname`. The most common questions users ask of a parse tree — "what tables?", "what
columns?", "what functions?" — each require 5-10 lines of boilerplate using `walk()` or a `Visitor` subclass.

## Goals / Non-Goals

**Goals:**

- Provide a generic `find_nodes(tree, node_type)` iterator for filtering a parse tree by protobuf message type.
- Provide three specific helpers (`extract_tables`, `extract_columns`, `extract_functions`) built on `find_nodes` that
  answer the most common AST questions in a single call.
- `find_nodes` returns protobuf messages; the `extract_*` helpers return simple Python strings so callers don't need
  protobuf knowledge.
- Accept any protobuf `Message` as input — works with `ParseResult`, individual statements, or any subtree.

**Non-Goals:**

- Full SQL analysis (e.g., distinguishing read vs. write tables, resolving aliases, tracking column-to-table bindings).
  These are significantly more complex and can be added later.
- Returning structured objects (e.g., dataclasses with schema/catalog fields). Strings keep the API simple; users who
  need richer data can use `walk()` or `Visitor` directly.
- Supporting non-protobuf inputs (raw SQL strings). Users should call `parse()` first.

## Decisions

### 1. Generic `find_nodes()` as the foundation

`find_nodes(tree, node_type)` takes a protobuf `Message` and a node type string (e.g., `"RangeVar"`) and yields all
matching messages from the tree. It uses `walk()` internally and filters by `type(node).DESCRIPTOR.name`. The
`extract_*` helpers are thin wrappers that call `find_nodes` and then extract string fields from the matched nodes.

This layering gives users two levels of abstraction:

- `find_nodes` — get the raw protobuf nodes of a specific type (for custom analysis)
- `extract_*` — get simple strings for the most common questions

`find_nodes` returns a `Generator` (lazy) so callers can stop early or compose with other itertools.

*Alternative*: Only expose the `extract_*` functions and keep node filtering internal. But users frequently need access
to the actual nodes (e.g., to read `RangeVar.alias` or `FuncCall.args`), so exposing `find_nodes` avoids forcing them
back to raw `walk()` + manual filtering.

### 2. Return `list[str]` with dot-qualified names

- `extract_tables`: `"schema.table"` when schema is present, `"table"` otherwise. Uses `RangeVar.schemaname` and
  `RangeVar.relname`.
- `extract_columns`: `"table.column"` when qualified, `"column"` otherwise. Extracts `String.sval` from
  `ColumnRef.fields` nodes.
- `extract_functions`: `"schema.func"` when schema-qualified, `"func"` otherwise. Extracts `String.sval` from
  `FuncCall.funcname` nodes.

Dot-qualified strings match how users write SQL and are easy to work with. Duplicates are preserved (a table referenced
twice appears twice) — callers can deduplicate with `set()` if needed.

*Alternative*: Return `set[str]`. Loses ordering and frequency information. Users who want unique values can trivially
wrap in `set()`.

*Alternative*: Return tuples like `("schema", "table")`. More structured but less ergonomic for the common case. The
dot-joined string matches SQL syntax.

### 3. Single `_helpers.py` module

All three functions go in one internal module. They share the same pattern (walk + filter + extract strings) so
splitting would be over-engineering. Following the existing convention of underscore-prefixed internal modules
(`_parse.py`, `_walk.py`, etc.).

### 4. Filter by protobuf descriptor name

Use `type(node).DESCRIPTOR.name` to identify node types during `walk()`, matching the pattern already used in
`Visitor.visit()`. This avoids importing concrete protobuf classes and stays consistent with the existing codebase.

### 5. Handle `ColumnRef.fields` and `FuncCall.funcname` Node wrappers

Both `ColumnRef.fields` and `FuncCall.funcname` are `repeated Node` — each element is a `Node` oneof wrapper containing
a `String` (for identifiers) or `A_Star` (for `*`). The helpers will unwrap the `Node` wrapper using `_unwrap_node()`
from `_walk.py`, filter for `String` descriptors, and extract `.sval`.

For `extract_columns`, `*` references (e.g., `SELECT *`) will be represented as `"*"`.

## Risks / Trade-offs

- **Incomplete extraction** — `extract_tables` finds `RangeVar` nodes, which covers `FROM`, `JOIN`, `INSERT INTO`,
  `UPDATE`, `DELETE FROM`, etc. However, tables referenced only via string literals (e.g., in `EXECUTE` or dynamic SQL)
  won't be found. This is acceptable — static analysis of the AST is inherently limited to what the parser represents as
  nodes. → Document this limitation in docstrings.

- **No deduplication** — returning all occurrences (including duplicates) gives callers full information but may
  surprise users expecting unique results. → Document that callers should use `set()` for unique values.

- **`ColumnRef` includes all column references** — no distinction between `SELECT` list, `WHERE` clause, `ORDER BY`,
  etc. → This is a non-goal; users needing positional context should use `walk()` or `Visitor` directly.
