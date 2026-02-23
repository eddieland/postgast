# ast-navigation Specification

## Purpose

Utilities for navigating and extracting information from protobuf AST trees produced by `parse()`. Includes a low-level
`walk()` generator and `Visitor` base class for generic tree traversal, plus high-level helper functions for common
extraction tasks (tables, columns, functions, DROP statement generation).

______________________________________________________________________

## Tree Walking

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

### Requirement: Public API export (walk and Visitor)

The `walk` function and `Visitor` class SHALL be importable directly from the `postgast` package (i.e.,
`from postgast import walk, Visitor`).

______________________________________________________________________

## AST Helpers

### Requirement: find_nodes yields all nodes of a given type from a parse tree

`find_nodes(tree, node_type)` SHALL accept any protobuf `Message` and a `node_type` string (the protobuf descriptor
name, e.g., `"RangeVar"`, `"SelectStmt"`), and yield all matching protobuf `Message` instances found in the tree.

- Results SHALL be yielded in depth-first pre-order (same order as `walk()`).
- The function SHALL return a `Generator` (lazy iteration).
- If no nodes of the given type exist, the generator SHALL yield nothing.
- `Node` oneof wrappers SHALL be transparently unwrapped (matching the behavior of `walk()`).

#### Scenario: Find all RangeVar nodes

- **WHEN** `find_nodes` is called on the parse result of `SELECT * FROM users JOIN orders ON users.id = orders.user_id`
  with `node_type="RangeVar"`
- **THEN** it SHALL yield two `RangeVar` messages with `relname` values `"users"` and `"orders"`

#### Scenario: No matching nodes

- **WHEN** `find_nodes` is called on the parse result of `SELECT 1` with `node_type="RangeVar"`
- **THEN** it SHALL yield nothing (empty iterator)

#### Scenario: Works on subtrees

- **WHEN** `find_nodes` is called on a `SelectStmt` node (not the full `ParseResult`) with `node_type="ColumnRef"`
- **THEN** it SHALL yield only `ColumnRef` nodes within that subtree

#### Scenario: Lazy evaluation

- **WHEN** a caller iterates `find_nodes` and stops after the first result (e.g., `next(find_nodes(...))`)
- **THEN** the function SHALL not traverse the entire tree

### Requirement: extract_tables returns table names from a parse tree

`extract_tables(tree)` SHALL accept any protobuf `Message` (e.g., `ParseResult`, `SelectStmt`, or any subtree) and
return a `list[str]` of table names found by collecting all `RangeVar` nodes in the tree.

- When a `RangeVar` has a non-empty `schemaname`, the result SHALL be `"schemaname.relname"`.
- When a `RangeVar` has no `schemaname`, the result SHALL be `"relname"` only.
- Results SHALL preserve encounter order (depth-first pre-order) and include duplicates.

#### Scenario: Simple SELECT with one table

- **WHEN** `extract_tables` is called on the parse result of `SELECT * FROM users`
- **THEN** the return value SHALL be `["users"]`

#### Scenario: Schema-qualified table

- **WHEN** `extract_tables` is called on the parse result of `SELECT * FROM public.users`
- **THEN** the return value SHALL be `["public.users"]`

#### Scenario: JOIN with multiple tables

- **WHEN** `extract_tables` is called on the parse result of
  `SELECT * FROM orders JOIN customers ON orders.id = customers.order_id`
- **THEN** the return value SHALL be `["orders", "customers"]`

#### Scenario: Subquery does not produce a RangeVar for the subquery itself

- **WHEN** `extract_tables` is called on the parse result of `SELECT * FROM (SELECT * FROM users) AS sub`
- **THEN** the return value SHALL be `["users"]` (the subquery alias is not a table)

#### Scenario: INSERT, UPDATE, DELETE target tables

- **WHEN** `extract_tables` is called on the parse result of `INSERT INTO logs SELECT * FROM events`
- **THEN** the return value SHALL be `["logs", "events"]`

#### Scenario: Duplicate table references are preserved

- **WHEN** `extract_tables` is called on the parse result of `SELECT * FROM t1 JOIN t1 ON t1.a = t1.b`
- **THEN** the return value SHALL be `["t1", "t1"]`

### Requirement: extract_columns returns column references from a parse tree

`extract_columns(tree)` SHALL accept any protobuf `Message` and return a `list[str]` of column references found by
collecting all `ColumnRef` nodes in the tree.

- Column names SHALL be dot-joined from the `String.sval` values in `ColumnRef.fields`.
- A single-element `ColumnRef` (e.g., `name`) SHALL produce `"name"`.
- A two-element `ColumnRef` (e.g., `t.name`) SHALL produce `"t.name"`.
- A `ColumnRef` containing an `A_Star` node (e.g., `SELECT *`) SHALL produce `"*"`.
- A qualified star (e.g., `t.*`) SHALL produce `"t.*"`.
- Results SHALL preserve encounter order and include duplicates.

#### Scenario: Simple column references

- **WHEN** `extract_columns` is called on the parse result of `SELECT name, age FROM users`
- **THEN** the return value SHALL be `["name", "age"]`

#### Scenario: Table-qualified columns

- **WHEN** `extract_columns` is called on the parse result of `SELECT u.name FROM users u`
- **THEN** the return value SHALL be `["u.name"]`

#### Scenario: Star expansion

- **WHEN** `extract_columns` is called on the parse result of `SELECT * FROM users`
- **THEN** the return value SHALL be `["*"]`

#### Scenario: Qualified star

- **WHEN** `extract_columns` is called on the parse result of `SELECT u.* FROM users u`
- **THEN** the return value SHALL be `["u.*"]`

#### Scenario: Columns in WHERE clause are included

- **WHEN** `extract_columns` is called on the parse result of `SELECT name FROM users WHERE age > 18`
- **THEN** the return value SHALL include both `"name"` and `"age"`

### Requirement: extract_functions returns function call names from a parse tree

`extract_functions(tree)` SHALL accept any protobuf `Message` and return a `list[str]` of function names found by
collecting all `FuncCall` nodes in the tree.

- Function names SHALL be dot-joined from the `String.sval` values in `FuncCall.funcname`.
- An unqualified function call (e.g., `count(*)`) SHALL produce `"count"`.
- A schema-qualified function call (e.g., `pg_catalog.now()`) SHALL produce `"pg_catalog.now"`.
- Results SHALL preserve encounter order and include duplicates.

#### Scenario: Simple function call

- **WHEN** `extract_functions` is called on the parse result of `SELECT count(*) FROM users`
- **THEN** the return value SHALL be `["count"]`

#### Scenario: Multiple function calls

- **WHEN** `extract_functions` is called on the parse result of `SELECT lower(name), upper(city) FROM users`
- **THEN** the return value SHALL be `["lower", "upper"]`

#### Scenario: Schema-qualified function

- **WHEN** `extract_functions` is called on the parse result of `SELECT pg_catalog.now()`
- **THEN** the return value SHALL be `["pg_catalog.now"]`

#### Scenario: Nested function calls

- **WHEN** `extract_functions` is called on the parse result of `SELECT upper(trim(name)) FROM users`
- **THEN** the return value SHALL include both `"upper"` and `"trim"`

### Requirement: to_drop produces DROP FUNCTION from CREATE FUNCTION

`to_drop(sql)` SHALL accept a `CREATE FUNCTION` statement and return the corresponding `DROP FUNCTION` statement. The
DROP signature SHALL include only parameter types (no parameter names), matching PostgreSQL's
`pg_get_function_identity_arguments()` format.

#### Scenario: Simple function with named parameters

- **WHEN** `to_drop` is called with
  `CREATE FUNCTION public.add(a integer, b integer) RETURNS integer LANGUAGE sql AS $$ SELECT a + b $$`
- **THEN** it SHALL return `DROP FUNCTION public.add(int, int)`

#### Scenario: No-argument function

- **WHEN** `to_drop` is called with `CREATE FUNCTION do_stuff() RETURNS void LANGUAGE sql AS $$ SELECT 1 $$`
- **THEN** it SHALL return `DROP FUNCTION do_stuff()`

#### Scenario: OUT parameters are excluded from the signature

- **WHEN** `to_drop` is called with
  `CREATE FUNCTION get_pair(IN x int, OUT a int, OUT b int) RETURNS RECORD LANGUAGE sql AS $$ SELECT 1, 2 $$`
- **THEN** it SHALL return `DROP FUNCTION get_pair(int)`

#### Scenario: VARIADIC parameter

- **WHEN** `to_drop` is called with
  `CREATE FUNCTION concat_all(VARIADIC items text[]) RETURNS text LANGUAGE sql AS $$ SELECT array_to_string(items, ',') $$`
- **THEN** it SHALL return `DROP FUNCTION concat_all(text[])`

#### Scenario: Unqualified function name

- **WHEN** `to_drop` is called with `CREATE FUNCTION myfunc(x int) RETURNS int LANGUAGE sql AS $$ SELECT x $$`
- **THEN** it SHALL return `DROP FUNCTION myfunc(int)`

#### Scenario: Quoted identifiers are preserved

- **WHEN** `to_drop` is called with
  `CREATE FUNCTION "My Schema"."My Func"("My Param" integer) RETURNS integer LANGUAGE sql AS $$ SELECT 1 $$`
- **THEN** it SHALL return `DROP FUNCTION "My Schema"."My Func"(int)`

#### Scenario: CREATE OR REPLACE is handled

- **WHEN** `to_drop` is called with
  `CREATE OR REPLACE FUNCTION public.add(a integer, b integer) RETURNS integer LANGUAGE sql AS $$ SELECT a + b $$`
- **THEN** it SHALL return `DROP FUNCTION public.add(int, int)`

### Requirement: to_drop produces DROP PROCEDURE from CREATE PROCEDURE

`to_drop(sql)` SHALL accept a `CREATE PROCEDURE` statement and return the corresponding `DROP PROCEDURE` statement,
using the same parameter-filtering rules as functions.

#### Scenario: Simple procedure

- **WHEN** `to_drop` is called with `CREATE PROCEDURE do_thing(x int) LANGUAGE sql AS $$ SELECT 1 $$`
- **THEN** it SHALL return `DROP PROCEDURE do_thing(int)`

### Requirement: to_drop produces DROP TRIGGER from CREATE TRIGGER

`to_drop(sql)` SHALL accept a `CREATE TRIGGER` statement and return the corresponding `DROP TRIGGER ... ON table`
statement.

#### Scenario: Schema-qualified trigger

- **WHEN** `to_drop` is called with
  `CREATE TRIGGER my_trg BEFORE INSERT ON public.t FOR EACH ROW EXECUTE FUNCTION public.fn()`
- **THEN** it SHALL return `DROP TRIGGER my_trg ON public.t`

#### Scenario: Unqualified trigger

- **WHEN** `to_drop` is called with `CREATE TRIGGER my_trg BEFORE INSERT ON t FOR EACH ROW EXECUTE FUNCTION fn()`
- **THEN** it SHALL return `DROP TRIGGER my_trg ON t`

### Requirement: to_drop produces DROP VIEW from CREATE VIEW

`to_drop(sql)` SHALL accept a `CREATE VIEW` statement and return the corresponding `DROP VIEW` statement.

#### Scenario: Schema-qualified view

- **WHEN** `to_drop` is called with `CREATE VIEW public.v AS SELECT 1`
- **THEN** it SHALL return `DROP VIEW public.v`

#### Scenario: Unqualified view

- **WHEN** `to_drop` is called with `CREATE VIEW v AS SELECT 1`
- **THEN** it SHALL return `DROP VIEW v`

#### Scenario: CREATE OR REPLACE VIEW is handled

- **WHEN** `to_drop` is called with `CREATE OR REPLACE VIEW public.v AS SELECT 1`
- **THEN** it SHALL return `DROP VIEW public.v`

### Requirement: to_drop raises ValueError on unsupported input

`to_drop(sql)` SHALL raise `ValueError` when the input is not a single CREATE FUNCTION, CREATE PROCEDURE, CREATE
TRIGGER, or CREATE VIEW statement.

#### Scenario: Unsupported statement type

- **WHEN** `to_drop` is called with `SELECT 1`
- **THEN** it SHALL raise `ValueError`

#### Scenario: Multi-statement input

- **WHEN** `to_drop` is called with `CREATE VIEW v AS SELECT 1; CREATE VIEW w AS SELECT 2`
- **THEN** it SHALL raise `ValueError`

#### Scenario: Empty input

- **WHEN** `to_drop` is called with an empty string
- **THEN** it SHALL raise either `ValueError` or `PgQueryError`

### Requirement: to_drop raises PgQueryError on invalid SQL

`to_drop(sql)` SHALL propagate `PgQueryError` when the input is not valid SQL (the error comes from `parse()`).

#### Scenario: Syntax error

- **WHEN** `to_drop` is called with `CREATE FUNCTION (`
- **THEN** it SHALL raise `PgQueryError`

### Requirement: All helpers accept any protobuf Message as input

All helper functions (`extract_tables`, `extract_columns`, `extract_functions`, `extract_function_identity`,
`extract_trigger_identity`) SHALL accept any `google.protobuf.message.Message` instance as input, including
`ParseResult`, individual statement nodes (e.g., `SelectStmt`), or any subtree node.

#### Scenario: Works on ParseResult

- **WHEN** any helper is called with the `ParseResult` returned by `postgast.parse()`
- **THEN** it SHALL traverse the entire parse tree and return results

#### Scenario: Works on a subtree node

- **WHEN** any helper is called with a `SelectStmt` extracted from a `ParseResult`
- **THEN** it SHALL traverse only that subtree and return results from within it

### Requirement: All helpers are exported from the postgast package

`find_nodes`, `extract_tables`, `extract_columns`, `extract_functions`, `extract_function_identity`,
`extract_trigger_identity`, `FunctionIdentity`, `TriggerIdentity`, and `to_drop` SHALL be importable directly from the
`postgast` package (i.e., `from postgast import extract_function_identity`).

#### Scenario: Direct import

- **WHEN** a user writes
  `from postgast import extract_function_identity, extract_trigger_identity, FunctionIdentity, TriggerIdentity`
- **THEN** the import SHALL succeed without errors

#### Scenario: to_drop import

- **WHEN** a user writes `from postgast import to_drop`
- **THEN** the import SHALL succeed without errors
