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
