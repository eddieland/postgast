## Requirements

### Requirement: extract_function_identity returns the identity of a CREATE FUNCTION statement

`extract_function_identity(tree)` SHALL accept any protobuf `Message` and return a `FunctionIdentity` NamedTuple or
`None`.

- `FunctionIdentity` SHALL be a `typing.NamedTuple` with fields `schema: str | None` and `name: str`.
- The function SHALL find the first `CreateFunctionStmt` node in the tree where `is_procedure` is `False`.
- When `funcname` contains two elements (schema-qualified), `schema` SHALL be the first element's `sval` and `name`
  SHALL be the second element's `sval`.
- When `funcname` contains one element (unqualified), `schema` SHALL be `None` and `name` SHALL be that element's
  `sval`.
- If no matching `CreateFunctionStmt` is found, the function SHALL return `None`.
- `CreateFunctionStmt` nodes with `is_procedure=True` SHALL be skipped.

#### Scenario: Schema-qualified function

- **WHEN** `extract_function_identity` is called on the parse result of
  `CREATE FUNCTION public.add(a integer, b integer) RETURNS integer AS $$ SELECT a + b $$ LANGUAGE sql`
- **THEN** the return value SHALL be `FunctionIdentity(schema="public", name="add")`

#### Scenario: Unqualified function

- **WHEN** `extract_function_identity` is called on the parse result of
  `CREATE FUNCTION my_func() RETURNS void AS $$ $$ LANGUAGE sql`
- **THEN** the return value SHALL be `FunctionIdentity(schema=None, name="my_func")`

#### Scenario: CREATE OR REPLACE FUNCTION

- **WHEN** `extract_function_identity` is called on the parse result of
  `CREATE OR REPLACE FUNCTION myschema.do_stuff() RETURNS void AS $$ $$ LANGUAGE sql`
- **THEN** the return value SHALL be `FunctionIdentity(schema="myschema", name="do_stuff")`

#### Scenario: Procedure is skipped

- **WHEN** `extract_function_identity` is called on the parse result of
  `CREATE PROCEDURE public.my_proc() LANGUAGE sql AS $$ $$ `
- **THEN** the return value SHALL be `None`

#### Scenario: No CREATE FUNCTION in tree

- **WHEN** `extract_function_identity` is called on the parse result of `SELECT 1`
- **THEN** the return value SHALL be `None`

#### Scenario: Comments and whitespace before name

- **WHEN** `extract_function_identity` is called on the parse result of
  `CREATE FUNCTION /* comment */ public.add(a int, b int) RETURNS int AS $$ SELECT a + b $$ LANGUAGE sql`
- **THEN** the return value SHALL be `FunctionIdentity(schema="public", name="add")`

### Requirement: extract_trigger_identity returns the identity of a CREATE TRIGGER statement

`extract_trigger_identity(tree)` SHALL accept any protobuf `Message` and return a `TriggerIdentity` NamedTuple or
`None`.

- `TriggerIdentity` SHALL be a `typing.NamedTuple` with fields `trigger: str`, `schema: str | None`, and `table: str`.
- The function SHALL find the first `CreateTrigStmt` node in the tree.
- `trigger` SHALL be the value of `trigname`.
- `schema` SHALL be the value of `relation.schemaname`, or `None` if `relation.schemaname` is empty.
- `table` SHALL be the value of `relation.relname`.
- If no `CreateTrigStmt` is found, the function SHALL return `None`.

#### Scenario: Schema-qualified trigger table

- **WHEN** `extract_trigger_identity` is called on the parse result of
  `CREATE TRIGGER my_trg AFTER INSERT ON public.orders FOR EACH ROW EXECUTE FUNCTION notify()`
- **THEN** the return value SHALL be `TriggerIdentity(trigger="my_trg", schema="public", table="orders")`

#### Scenario: Unqualified trigger table

- **WHEN** `extract_trigger_identity` is called on the parse result of
  `CREATE TRIGGER audit_trg BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION audit()`
- **THEN** the return value SHALL be `TriggerIdentity(trigger="audit_trg", schema=None, table="users")`

#### Scenario: CREATE OR REPLACE TRIGGER

- **WHEN** `extract_trigger_identity` is called on the parse result of
  `CREATE OR REPLACE TRIGGER my_trg AFTER INSERT ON myschema.events FOR EACH ROW EXECUTE FUNCTION log_event()`
- **THEN** the return value SHALL be `TriggerIdentity(trigger="my_trg", schema="myschema", table="events")`

#### Scenario: No CREATE TRIGGER in tree

- **WHEN** `extract_trigger_identity` is called on the parse result of `SELECT 1`
- **THEN** the return value SHALL be `None`

### Requirement: FunctionIdentity and TriggerIdentity support tuple unpacking

Both `FunctionIdentity` and `TriggerIdentity` SHALL be `typing.NamedTuple` subclasses and support positional unpacking.

#### Scenario: Unpack FunctionIdentity

- **WHEN** a caller writes `schema, name = extract_function_identity(tree)` on a tree containing
  `CREATE FUNCTION public.add() RETURNS void AS $$ $$ LANGUAGE sql`
- **THEN** `schema` SHALL be `"public"` and `name` SHALL be `"add"`

#### Scenario: Unpack TriggerIdentity

- **WHEN** a caller writes `trigger, schema, table = extract_trigger_identity(tree)` on a tree containing
  `CREATE TRIGGER t AFTER INSERT ON public.orders FOR EACH ROW EXECUTE FUNCTION f()`
- **THEN** `trigger` SHALL be `"t"`, `schema` SHALL be `"public"`, and `table` SHALL be `"orders"`
