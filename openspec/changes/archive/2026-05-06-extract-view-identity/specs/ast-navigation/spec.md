## ADDED Requirements

### Requirement: ViewIdentity type

The module SHALL provide a `ViewIdentity` NamedTuple with fields `schema: str | None` and `name: str` representing the
qualified identity of a `CREATE VIEW` statement.

#### Scenario: Schema-qualified view

- **WHEN** a user constructs `ViewIdentity(schema="public", name="active_users")`
- **THEN** the fields are accessible as `.schema` and `.name` with the given values

#### Scenario: Unqualified view

- **WHEN** a user constructs `ViewIdentity(schema=None, name="active_users")`
- **THEN** `.schema` is `None` and `.name` is `"active_users"`

### Requirement: extract_view_identity function

The module SHALL provide an `extract_view_identity(tree: Message) -> ViewIdentity | None` function that finds the first
`ViewStmt` node in the parse tree and returns a `ViewIdentity` containing the view's schema and name. The `schema` field
SHALL be `None` when the view is not schema-qualified.

#### Scenario: Schema-qualified CREATE VIEW

- **WHEN** `extract_view_identity` is called with the `ParseResult` from
  `"CREATE VIEW public.active_users AS SELECT id FROM users WHERE active"`
- **THEN** it returns `ViewIdentity(schema="public", name="active_users")`

#### Scenario: Unqualified CREATE VIEW

- **WHEN** `extract_view_identity` is called with the `ParseResult` from `"CREATE VIEW active_users AS SELECT 1"`
- **THEN** it returns `ViewIdentity(schema=None, name="active_users")`

#### Scenario: CREATE OR REPLACE VIEW

- **WHEN** `extract_view_identity` is called with the `ParseResult` from `"CREATE OR REPLACE VIEW v AS SELECT 1"`
- **THEN** it returns `ViewIdentity(schema=None, name="v")`

#### Scenario: No view in tree

- **WHEN** `extract_view_identity` is called with the `ParseResult` from `"SELECT 1"`
- **THEN** it returns `None`

#### Scenario: Returns first view when multiple views present

- **WHEN** `extract_view_identity` is called with a `ParseResult` containing two `CREATE VIEW` statements
- **THEN** it returns the `ViewIdentity` for the first view only

### Requirement: IndexIdentity type

The module SHALL provide an `IndexIdentity` NamedTuple with fields `schema: str | None` and `name: str` representing the
qualified identity of a `CREATE INDEX` statement. The `schema` is taken from the index's target table relation (since
PostgreSQL places an index in the same schema as its table). The `name` is the index name.

#### Scenario: Schema-qualified CREATE INDEX

- **WHEN** a user constructs `IndexIdentity(schema="public", name="idx_users_email")`
- **THEN** the fields are accessible as `.schema` and `.name` with the given values

#### Scenario: Unqualified index

- **WHEN** a user constructs `IndexIdentity(schema=None, name="idx_users_email")`
- **THEN** `.schema` is `None`

### Requirement: extract_index_identity function

The module SHALL provide an `extract_index_identity(tree: Message) -> IndexIdentity | None` function that finds the
first `IndexStmt` node in the parse tree and returns an `IndexIdentity`. The `schema` field is sourced from
`IndexStmt.relation.schemaname` (the target table's schema) and SHALL be `None` when not schema-qualified. The `name`
field is sourced from `IndexStmt.idxname`.

#### Scenario: Schema-qualified CREATE INDEX

- **WHEN** `extract_index_identity` is called with the `ParseResult` from
  `"CREATE INDEX idx_users_email ON public.users(email)"`
- **THEN** it returns `IndexIdentity(schema="public", name="idx_users_email")`

#### Scenario: Unqualified CREATE INDEX

- **WHEN** `extract_index_identity` is called with the `ParseResult` from `"CREATE INDEX idx_name ON orders(total)"`
- **THEN** it returns `IndexIdentity(schema=None, name="idx_name")`

#### Scenario: No index in tree

- **WHEN** `extract_index_identity` is called with the `ParseResult` from `"SELECT 1"`
- **THEN** it returns `None`

### Requirement: SequenceIdentity type

The module SHALL provide a `SequenceIdentity` NamedTuple with fields `schema: str | None` and `name: str` representing
the qualified identity of a `CREATE SEQUENCE` statement.

#### Scenario: Schema-qualified sequence

- **WHEN** a user constructs `SequenceIdentity(schema="public", name="order_id_seq")`
- **THEN** the fields are accessible as `.schema` and `.name` with the given values

#### Scenario: Unqualified sequence

- **WHEN** a user constructs `SequenceIdentity(schema=None, name="order_id_seq")`
- **THEN** `.schema` is `None`

### Requirement: extract_sequence_identity function

The module SHALL provide an `extract_sequence_identity(tree: Message) -> SequenceIdentity | None` function that finds
the first `CreateSeqStmt` node in the parse tree and returns a `SequenceIdentity` from
`CreateSeqStmt.sequence.{schemaname,relname}`. The `schema` field SHALL be `None` when not schema-qualified.

#### Scenario: Schema-qualified CREATE SEQUENCE

- **WHEN** `extract_sequence_identity` is called with the `ParseResult` from `"CREATE SEQUENCE public.order_id_seq"`
- **THEN** it returns `SequenceIdentity(schema="public", name="order_id_seq")`

#### Scenario: Unqualified CREATE SEQUENCE

- **WHEN** `extract_sequence_identity` is called with the `ParseResult` from `"CREATE SEQUENCE order_id_seq"`
- **THEN** it returns `SequenceIdentity(schema=None, name="order_id_seq")`

#### Scenario: No sequence in tree

- **WHEN** `extract_sequence_identity` is called with the `ParseResult` from `"SELECT 1"`
- **THEN** it returns `None`

### Requirement: SchemaIdentity type

The module SHALL provide a `SchemaIdentity` NamedTuple with a single field `name: str` representing the identity of a
`CREATE SCHEMA` statement. Schemas are top-level namespace objects and have no parent schema qualifier.

#### Scenario: SchemaIdentity construction

- **WHEN** a user constructs `SchemaIdentity(name="analytics")`
- **THEN** `.name` is `"analytics"`

### Requirement: extract_schema_identity function

The module SHALL provide an `extract_schema_identity(tree: Message) -> SchemaIdentity | None` function that finds the
first `CreateSchemaStmt` node in the parse tree and returns a `SchemaIdentity` from `CreateSchemaStmt.schemaname`.

#### Scenario: CREATE SCHEMA

- **WHEN** `extract_schema_identity` is called with the `ParseResult` from `"CREATE SCHEMA analytics"`
- **THEN** it returns `SchemaIdentity(name="analytics")`

#### Scenario: No schema in tree

- **WHEN** `extract_schema_identity` is called with the `ParseResult` from `"SELECT 1"`
- **THEN** it returns `None`

## MODIFIED Requirements

### Requirement: All helpers accept any protobuf Message as input

All helper functions (`extract_tables`, `extract_columns`, `extract_functions`, `extract_function_identity`,
`extract_trigger_identity`, `extract_view_identity`, `extract_index_identity`, `extract_sequence_identity`,
`extract_schema_identity`) SHALL accept any `google.protobuf.message.Message` instance as input, including
`ParseResult`, individual statement nodes (e.g., `SelectStmt`), or any subtree node.

#### Scenario: Works on ParseResult

- **WHEN** any helper is called with the `ParseResult` returned by `postgast.parse()`
- **THEN** it SHALL traverse the entire parse tree and return results

#### Scenario: Works on a subtree node

- **WHEN** any helper is called with a `SelectStmt` extracted from a `ParseResult`
- **THEN** it SHALL traverse only that subtree and return results from within it

### Requirement: All helpers are exported from the postgast package

`find_nodes`, `extract_tables`, `extract_columns`, `extract_functions`, `extract_function_identity`,
`extract_trigger_identity`, `extract_view_identity`, `extract_index_identity`, `extract_sequence_identity`,
`extract_schema_identity`, `FunctionIdentity`, `TriggerIdentity`, `ViewIdentity`, `IndexIdentity`, `SequenceIdentity`,
`SchemaIdentity`, and `to_drop` SHALL be importable directly from the `postgast` package.

#### Scenario: Direct import of new identity helpers

- **WHEN** a user writes
  `from postgast import extract_view_identity, extract_index_identity, extract_sequence_identity, extract_schema_identity, ViewIdentity, IndexIdentity, SequenceIdentity, SchemaIdentity`
- **THEN** the import SHALL succeed without errors

#### Scenario: to_drop import

- **WHEN** a user writes `from postgast import to_drop`
- **THEN** the import SHALL succeed without errors
