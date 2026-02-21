## ADDED Requirements

### Requirement: walk function

The module SHALL provide a `walk(node)` generator function that performs a depth-first pre-order traversal of a protobuf
message tree, yielding `(field_name, message)` tuples for every protobuf message encountered. The `field_name` is the
protobuf field name that led to the message (e.g., `"where_clause"`, `"target_list"`), or an empty string for the root
node. The `node` argument SHALL accept any protobuf `Message` instance (e.g., `ParseResult`, `RawStmt`, `SelectStmt`).

#### Scenario: Walk a simple SELECT

- **WHEN** `walk` is called with the `ParseResult` from parsing `"SELECT 1"`
- **THEN** it yields tuples for every protobuf message in the tree, starting with `("", ParseResult)`, and includes the
  `RawStmt` and `SelectStmt` (among others)

#### Scenario: Walk yields field names

- **WHEN** `walk` is called with the `ParseResult` from parsing `"SELECT a FROM t WHERE x = 1"`
- **THEN** each yielded tuple contains the protobuf field name that led to the message (e.g., `"stmts"` for the
  `RawStmt`, `"where_clause"` for the expression node under the WHERE clause)

#### Scenario: Walk a subtree

- **WHEN** `walk` is called with a `SelectStmt` message (not a full `ParseResult`)
- **THEN** it traverses only the subtree rooted at that `SelectStmt`, yielding `("", SelectStmt)` first

#### Scenario: Walk multi-statement input

- **WHEN** `walk` is called with the `ParseResult` from parsing `"SELECT 1; CREATE TABLE t (id int)"`
- **THEN** it yields messages from both statements' subtrees

### Requirement: Node oneof unwrapping

When traversal encounters a `Node` protobuf message (the oneof wrapper), the walker SHALL automatically unwrap it and
yield the inner concrete message (e.g., `SelectStmt`, `ColumnRef`) rather than the `Node` wrapper itself. The field name
in the yielded tuple SHALL be the field name from the parent that contained the `Node`, not the oneof field name inside
`Node`.

#### Scenario: Node wrappers are transparent

- **WHEN** `walk` is called on a parse tree containing `Node` wrapper messages
- **THEN** no `Node` messages appear in the yielded results — only their unwrapped inner messages

#### Scenario: Unwrapping preserves field name

- **WHEN** a `SelectStmt` has a `where_clause` field of type `Node` containing a `BoolExpr`
- **THEN** `walk` yields `("where_clause", <BoolExpr instance>)`, not `("where_clause", <Node instance>)`

### Requirement: Child discovery via protobuf introspection

The walker SHALL discover child messages using `ListFields()` and `FieldDescriptor` introspection. It SHALL follow
singular message fields, repeated message fields, and typed (non-Node) message fields. It SHALL skip scalar fields
(strings, integers, enums, booleans).

#### Scenario: Singular message field traversal

- **WHEN** a `SelectStmt` has a singular `where_clause` field set
- **THEN** `walk` recurses into that field and yields its contents

#### Scenario: Repeated message field traversal

- **WHEN** a `SelectStmt` has a `target_list` repeated field containing multiple `Node` entries
- **THEN** `walk` recurses into each element and yields the unwrapped message from each

#### Scenario: Typed message field traversal

- **WHEN** a `SelectStmt` has a `with_clause` field of type `WithClause` (not wrapped in `Node`)
- **THEN** `walk` recurses into the `WithClause` and yields it

#### Scenario: Scalar fields are skipped

- **WHEN** a message has scalar fields (e.g., `stmt_location` int, `relname` string)
- **THEN** `walk` does not yield them — only protobuf messages are yielded

### Requirement: Visitor base class

The module SHALL provide a `Visitor` base class with the following methods:

- `visit(node)` — resolves the protobuf message type name via `type(node).DESCRIPTOR.name` and calls
  `visit_<TypeName>(node)` if defined on the subclass, otherwise calls `generic_visit(node)`.
- `generic_visit(node)` — recurses into all message-typed children of `node` by calling `self.visit()` on each.

Users subclass `Visitor` and override `visit_<TypeName>` methods to handle specific node types.

#### Scenario: Dispatch to visit_SelectStmt

- **WHEN** a `Visitor` subclass defines `visit_SelectStmt(self, node)` and `visit` is called with a `SelectStmt` message
- **THEN** the `visit_SelectStmt` method is called with that message

#### Scenario: Fallback to generic_visit

- **WHEN** a `Visitor` subclass does NOT define `visit_SelectStmt` and `visit` is called with a `SelectStmt` message
- **THEN** `generic_visit` is called, which recurses into the `SelectStmt`'s children

#### Scenario: User controls child recursion

- **WHEN** a `Visitor` subclass defines `visit_SelectStmt` without calling `self.generic_visit(node)`
- **THEN** children of that `SelectStmt` are NOT visited (the user owns the recursion decision)

#### Scenario: User opts into child recursion

- **WHEN** a `Visitor` subclass defines `visit_SelectStmt` and calls `self.generic_visit(node)` within it
- **THEN** children of that `SelectStmt` ARE visited after the custom logic runs

### Requirement: Visitor unwraps Node wrappers

The `Visitor` SHALL unwrap `Node` oneof wrappers the same way as `walk`. When `visit` is called with a `Node` message,
it SHALL unwrap it and dispatch to `visit_<InnerTypeName>` for the concrete inner message.

#### Scenario: Visitor dispatches through Node

- **WHEN** `visit` is called with a `Node` message containing a `ColumnRef`
- **THEN** `visit_ColumnRef` is called (not `visit_Node`)

### Requirement: Visitor collects results from a full tree

A `Visitor` subclass SHALL be usable to collect information across an entire parse tree by calling `visit` on the root
`ParseResult` and accumulating state in instance attributes.

#### Scenario: Collect all table names

- **WHEN** a `Visitor` subclass defines `visit_RangeVar` to collect table names and `visit` is called on the
  `ParseResult` from `"SELECT a FROM t1 JOIN t2 ON t1.id = t2.id"`
- **THEN** the visitor's accumulated state contains both `"t1"` and `"t2"`

### Requirement: Public API export

The `walk` function and `Visitor` class SHALL be importable directly from the `postgast` package (i.e.,
`from postgast import walk, Visitor`).

#### Scenario: Top-level import of walk

- **WHEN** user code runs `from postgast import walk`
- **THEN** the name resolves without error and is callable

#### Scenario: Top-level import of Visitor

- **WHEN** user code runs `from postgast import Visitor`
- **THEN** the name resolves without error and is a class that can be subclassed
