## Requirements

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

### Requirement: to_drop is exported from the postgast package

`to_drop` SHALL be importable directly from the `postgast` package (i.e., `from postgast import to_drop`).

#### Scenario: Direct import

- **WHEN** a user writes `from postgast import to_drop`
- **THEN** the import SHALL succeed without errors
