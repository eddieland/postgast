## Typed Tree Walking

### Overview

Typed alternatives to `walk()` and `Visitor` that work with `AstNode` wrappers from the `nodes` module. Provides the
same traversal semantics as the existing untyped APIs but with full type safety and IDE autocomplete.

### Public API

#### `postgast.walk_typed(node: AstNode) -> Generator[tuple[str, AstNode], None, None]`

Like `walk()` but accepts and yields typed `AstNode` wrappers. Depth-first pre-order traversal. The `field_name` in each
tuple is the protobuf field name that led to the node (empty string for the root).

#### `postgast.TypedVisitor`

Like `Visitor` but dispatches to handlers that receive typed wrappers. Subclass and override `visit_<TypeName>` methods
to handle specific node types.

Methods:

- `visit(node: AstNode)` — Resolves the wrapper class name and calls `visit_<ClassName>(node)` if defined, otherwise
  calls `generic_visit(node)`.
- `generic_visit(node: AstNode)` — Recurses into all child nodes by calling `self.visit()` on each.

### Behavioral Requirements

1. `walk_typed()` SHALL yield the same nodes in the same order as `walk()`, but as `AstNode` wrappers
1. `walk_typed()` SHALL never yield `Node` oneof wrappers — they are transparently unwrapped
1. `TypedVisitor` SHALL dispatch to `visit_SelectStmt(self, node: SelectStmt)` (not
   `visit_SelectStmt(self, node: Message)`)
1. `TypedVisitor` SHALL fall back to `generic_visit()` for unhandled node types
1. `TypedVisitor` SHALL unwrap `Node` oneof wrappers before dispatching
1. The existing `walk()` and `Visitor` SHALL remain unchanged (backward compatible)
1. Both `walk_typed()` and `TypedVisitor` SHALL be importable from the `postgast` package

### Scenarios

#### Scenario: walk_typed yields typed wrappers

- **WHEN** `walk_typed` is called on a wrapped `ParseResult` from `"SELECT 1"`
- **THEN** every yielded node is an instance of `AstNode` (not `Message`)

#### Scenario: TypedVisitor dispatches to typed handlers

- **WHEN** a `TypedVisitor` subclass defines `visit_SelectStmt(self, node: SelectStmt)` and `visit` is called with a
  wrapped `SelectStmt`
- **THEN** `visit_SelectStmt` is called with the `SelectStmt` wrapper

#### Scenario: TypedVisitor collects results

- **WHEN** a `TypedVisitor` subclass collects table names via `visit_RangeVar` and processes
  `"SELECT * FROM t1 JOIN t2 ON t1.id = t2.id"`
- **THEN** the visitor's accumulated state contains both `"t1"` and `"t2"`, accessed via `node.relname`
