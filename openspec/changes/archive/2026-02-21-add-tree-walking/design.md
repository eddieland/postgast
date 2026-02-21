## Context

postgast parses SQL into protobuf ASTs where every node in the tree is one of 130+ message types wrapped in a `Node`
oneof union. Users currently traverse these trees by hand — checking `WhichOneof('node')` at each `Node` wrapper,
knowing which fields on each message type contain children, and recursing manually. This change adds two complementary
traversal interfaces: an iterator-based `walk()` and a callback-based `Visitor` class.

The protobuf structure has three kinds of child references:

- **Singular `Node` fields** (e.g., `SelectStmt.where_clause`) — a oneof wrapper around a concrete message
- **Repeated `Node` fields** (e.g., `SelectStmt.target_list`) — lists of oneof wrappers
- **Typed message fields** (e.g., `SelectStmt.into_clause: IntoClause`, `SelectStmt.large: SelectStmt`) — direct message
  references without a `Node` wrapper

All three must be followed during traversal. Scalar fields (strings, ints, enums, bools) are leaves.

## Goals / Non-Goals

**Goals:**

- Provide a `walk()` function that yields every protobuf message in a parse tree via depth-first traversal
- Provide a `Visitor` base class that dispatches to `visit_<TypeName>` methods by message type
- Work with any protobuf message as the starting point (ParseResult, RawStmt, SelectStmt, etc.)
- Use protobuf descriptor introspection so traversal automatically covers all node types without maintaining a manual
  field map
- Be purely additive — no changes to existing API behavior

**Non-Goals:**

- Tree transformation / rewriting (protobuf messages are not easily mutable in-place; this is a read-only traversal API)
- Breadth-first or other traversal orders (DFS pre-order covers the common cases)
- Parent tracking or path context (can be layered on later without changing the core API)

## Decisions

### 1. Use protobuf `ListFields()` + descriptor introspection for child discovery

**Choice**: Discover children dynamically using `message.ListFields()` and checking `field_descriptor.message_type`.

**Alternatives considered**:

- *Manual field map per node type*: Would require maintaining a mapping of 130+ types to their child fields. Fragile,
  breaks when libpg_query updates the proto schema.
- *Proto reflection via `DESCRIPTOR.fields`*: Iterates all declared fields including unset ones. `ListFields()` only
  returns fields that are actually set, which is both faster and avoids visiting empty optional fields.

**Rationale**: `ListFields()` returns `(FieldDescriptor, value)` pairs for every set field. We check
`field_descriptor.type == FieldDescriptor.TYPE_MESSAGE` to identify message children, and
`field_descriptor.label == FieldDescriptor.LABEL_REPEATED` to handle lists. This is zero-maintenance — any new node
types added to the proto schema are traversed automatically.

### 2. Unwrap `Node` oneof wrappers transparently

**Choice**: When traversal encounters a `Node` message, it automatically unwraps the oneof to yield the inner concrete
message (e.g., `SelectStmt`) rather than the `Node` wrapper.

**Rationale**: The `Node` wrapper is a protobuf encoding artifact — users never want to operate on a `Node` itself, they
want the `SelectStmt` or `ColumnRef` inside it. Unwrapping means `walk()` yields useful types and `Visitor` dispatches
to `visit_SelectStmt` rather than `visit_Node`.

### 3. `walk()` as a generator yielding `(field_name, message)` tuples

**Choice**: `walk(root)` is a generator that yields `(field_name, message)` tuples during a pre-order depth-first
traversal. The `field_name` is the protobuf field name that led to this message (e.g., `"where_clause"`,
`"target_list"`), or an empty string for the root.

**Alternatives considered**:

- *Yield just the message*: Simpler, but without the field name users can't distinguish between e.g. `from_clause` nodes
  and `target_list` nodes when the contained message types are the same.
- *Yield a rich context object (path, depth, parent)*: More powerful but heavier. Can be added later as a separate
  function without changing `walk()`.

**Rationale**: The tuple provides enough context for common filtering tasks (e.g., "find all `where_clause` nodes") with
minimal overhead. The field name is free — it comes from the `FieldDescriptor` we already have.

### 4. `Visitor` base class with `visit_<TypeName>` dispatch

**Choice**: A `Visitor` base class with:

- `visit(node)` — entry point. Resolves the message type name and calls `visit_<TypeName>(node)` if defined, else
  `generic_visit(node)`.
- `generic_visit(node)` — default: recurse into all message-typed children.
- Users subclass and override `visit_SelectStmt(self, node)`, etc.

**Alternatives considered**:

- *Functional visitor (pass a dict of callbacks)*: Less discoverable, harder to type-check. Class-based is idiomatic
  Python for this pattern (cf. `ast.NodeVisitor`).
- *Separate `NodeVisitor` and `NodeTransformer`*: Premature — transforming protobuf messages is a non-goal. Just provide
  the read-only visitor.

**Rationale**: Mirrors Python's `ast.NodeVisitor` which is well-understood. Method dispatch via
`getattr(self, f"visit_{type_name}", self.generic_visit)` is simple and fast.

### 5. Type name for dispatch uses protobuf message name

**Choice**: Use `type(node).DESCRIPTOR.name` (e.g., `"SelectStmt"`, `"ColumnRef"`) for visitor method dispatch.

**Alternatives considered**:

- *Python class name `type(node).__name__`*: Same as descriptor name for generated protobuf classes, but descriptor name
  is the canonical source.
- *snake_case names*: Would mismatch the protobuf schema and PostgreSQL naming. PascalCase matches both.

### 6. Single module `_walk.py`

**Choice**: All traversal code lives in `src/postgast/_walk.py`. Public API exports from `__init__.py`.

**Rationale**: The walk function and Visitor class are tightly coupled (Visitor uses the same child-discovery logic as
walk). One module keeps it simple.

## Risks / Trade-offs

- **Performance on large ASTs**: `ListFields()` + descriptor checks add overhead vs. hand-written traversal for a
  specific node type. → Acceptable for a utility API; users needing maximum performance can still traverse manually.
- **Protobuf API stability**: We depend on `ListFields()`, `WhichOneof()`, `DESCRIPTOR`, and `FieldDescriptor` constants
  from the `protobuf` library. → These are stable public APIs in both `protobuf` 4.x and 5.x.
- **No parent/path tracking**: Some use cases (e.g., "find all columns inside a WHERE clause") need to know the ancestor
  chain. → Can be added as a separate higher-level function later without breaking `walk()` or `Visitor`.
