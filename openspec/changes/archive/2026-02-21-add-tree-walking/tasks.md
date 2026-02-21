## 1. Core traversal logic

- [x] 1.1 Create `src/postgast/_walk.py` with a private `_unwrap_node(node)` helper that checks if a message is a `Node`
  (has a `node` oneof) and returns the inner concrete message, or returns the original message unchanged
- [x] 1.2 Implement a private `_iter_children(node)` generator that uses `ListFields()` and `FieldDescriptor` to yield
  `(field_name, child_message)` for all message-typed fields (singular and repeated), unwrapping `Node` wrappers via
  `_unwrap_node`
- [x] 1.3 Implement the public `walk(node)` generator that yields `("", root)` then recursively yields
  `(field_name, message)` for all descendants via `_iter_children`, performing DFS pre-order traversal

## 2. Visitor class

- [x] 2.1 Implement the `Visitor` base class with `visit(node)` that resolves `type(node).DESCRIPTOR.name`, unwraps
  `Node` wrappers, and dispatches to `visit_<TypeName>` or `generic_visit`
- [x] 2.2 Implement `generic_visit(node)` that iterates children via `_iter_children` and calls `self.visit()` on each

## 3. Public API

- [x] 3.1 Add `walk` and `Visitor` to `src/postgast/__init__.py` imports and `__all__`

## 4. Tests

- [x] 4.1 Test `walk` on a simple `SELECT 1` — verify it yields `ParseResult`, `RawStmt`, and `SelectStmt` with correct
  field names
- [x] 4.2 Test `walk` yields field names correctly for `SELECT a FROM t WHERE x = 1` (check for `"stmts"`,
  `"where_clause"`, `"target_list"`, `"from_clause"`)
- [x] 4.3 Test `walk` on a subtree — pass a `SelectStmt` directly and verify root tuple is `("", SelectStmt)`
- [x] 4.4 Test `walk` on multi-statement input covers both statements
- [x] 4.5 Test that no `Node` wrapper messages appear in `walk` output
- [x] 4.6 Test that scalar fields are not yielded by `walk`
- [x] 4.7 Test `Visitor` dispatches to `visit_SelectStmt` when defined
- [x] 4.8 Test `Visitor` falls back to `generic_visit` when no specific handler is defined
- [x] 4.9 Test that defining `visit_SelectStmt` without calling `generic_visit` skips children
- [x] 4.10 Test that calling `self.generic_visit(node)` inside a handler visits children
- [x] 4.11 Test `Visitor` unwraps `Node` wrappers (dispatches to `visit_ColumnRef`, not `visit_Node`)
- [x] 4.12 Test end-to-end: `Visitor` subclass that collects all table names from
  `SELECT a FROM t1 JOIN t2 ON t1.id = t2.id`
- [x] 4.13 Test `from postgast import walk, Visitor` resolves without error

## 5. Lint and format

- [x] 5.1 Run `make lint` and fix any type-check or formatting issues
