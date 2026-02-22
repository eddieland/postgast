## ADDED Requirements

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
