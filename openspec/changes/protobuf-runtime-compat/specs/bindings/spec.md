## MODIFIED Requirements

### Requirement: Generated protobuf module

The package SHALL provide a `pg_query_pb2` module whose message classes are constructed at import time from the
committed serialized descriptor set, using the public `descriptor_pool`, `descriptor_pb2`, `message_factory`, and
`enum_type_wrapper` APIs. The module SHALL NOT be protoc gencode and SHALL NOT invoke
`google.protobuf.runtime_version.ValidateProtobufRuntimeVersion`, so that no gencode/runtime version gate applies to it.

The module SHALL expose, at module level: every top-level message as a class, every top-level enum as an
`EnumTypeWrapper`, every top-level enum value as an integer constant, the file descriptor as `DESCRIPTOR`, and the pool
as `DESCRIPTOR_POOL`. This surface SHALL match what `protoc --python_out` publishes for the same schema, so that
`pg_query_pb2.pyi` remains an accurate stub.

#### Scenario: Module is importable

- **WHEN** the package is installed
- **THEN** `from postgast.pg_query_pb2 import ParseResult` succeeds without error

#### Scenario: ParseResult message structure

- **WHEN** the `ParseResult` message is inspected
- **THEN** it has an `int32 version` field and a `repeated RawStmt stmts` field matching the proto schema

#### Scenario: Imports on a protobuf runtime newer than the generating protoc

- **WHEN** the module is imported on a protobuf runtime whose major version is newer than the protoc release that
  produced the committed descriptor set
- **THEN** the import succeeds with no error and no version warning

#### Scenario: Imports on the declared minimum protobuf runtime

- **WHEN** the module is imported on the exact protobuf version named as the floor in `pyproject.toml` `dependencies`
- **THEN** the import succeeds and message classes are usable

#### Scenario: Top-level enum values are module constants

- **WHEN** user code reads `pg_query_pb2.AEXPR_OP`, `pg_query_pb2.SORTBY_ASC`, or `pg_query_pb2.AT_AddColumn`
- **THEN** each resolves to the integer value declared for it in the proto schema

#### Scenario: Enum wrappers behave as protoc enums

- **WHEN** user code calls `pg_query_pb2.A_Expr_Kind.Name(pg_query_pb2.AEXPR_OP)`
- **THEN** it returns `"AEXPR_OP"`, and `.Value("AEXPR_OP")` returns the same integer

#### Scenario: Nested types are reachable on their parent class

- **WHEN** user code accesses `pg_query_pb2.SummaryResult.Table` or `pg_query_pb2.SummaryResult.Context`
- **THEN** the nested message class and nested enum are available as attributes of the parent class

#### Scenario: Every descriptor entry is published

- **WHEN** the file descriptor is walked for top-level messages, top-level enums, and enum value names
- **THEN** a module attribute exists for each one

### Requirement: Protobuf runtime dependency

The package SHALL declare `protobuf>=5.29` as a runtime dependency in `pyproject.toml` `dependencies`, with no upper
version bound. This is the official Google protobuf library. The declared floor SHALL be a version that can actually
import `pg_query_pb2`.

#### Scenario: Dependency is installed automatically

- **WHEN** a user runs `pip install postgast`
- **THEN** the `protobuf` package is installed as a dependency

#### Scenario: Declared floor is importable

- **WHEN** the lowest protobuf version permitted by `dependencies` is installed
- **THEN** `import postgast` succeeds

#### Scenario: No upper bound blocks new majors

- **WHEN** a protobuf release with a newer major version than the one used during development is installed
- **THEN** the dependency declaration permits it and `import postgast` succeeds

### Requirement: Makefile regeneration target

The project SHALL provide a `make proto` target that regenerates the committed descriptor set and type stub from the
vendored proto file, invoking protoc with `--descriptor_set_out`, `--include_imports`, and `--pyi_out`. The target SHALL
NOT use `--python_out`, because `pg_query_pb2.py` is hand-written source rather than generated output. This target is
used by maintainers when the vendored `pg_query.proto` is updated.

#### Scenario: Regeneration produces identical output

- **WHEN** `make proto` is run without modifying the vendored proto file
- **THEN** the generated `pg_query.desc` and `pg_query_pb2.pyi` are byte-identical to the committed versions

#### Scenario: Regeneration reflects proto changes

- **WHEN** the vendored `pg_query.proto` is updated and `make proto` is run
- **THEN** `pg_query.desc` and `pg_query_pb2.pyi` reflect the updated proto definitions

#### Scenario: Loader is not overwritten

- **WHEN** `make proto` is run
- **THEN** `src/postgast/pg_query_pb2.py` is left untouched

## ADDED Requirements

### Requirement: Committed descriptor set

The package SHALL include a serialized `FileDescriptorSet` at `src/postgast/pg_query.desc`, produced by protoc from the
vendored `vendor/libpg_query/protobuf/pg_query.proto` with `--include_imports`. The file SHALL be committed to the
repository and shipped as package data in both the wheel and the sdist, so that users installing from either do not need
`protoc`.

#### Scenario: Descriptor ships in the installed package

- **WHEN** the package is installed from a wheel or an sdist
- **THEN** `pg_query.desc` is present alongside the `postgast` package modules and readable via `importlib.resources`

#### Scenario: Descriptor set is self-contained

- **WHEN** the descriptor set is parsed
- **THEN** every file it references is present in the set, ordered so that each file's dependencies precede it

#### Scenario: Descriptor matches the vendored schema

- **WHEN** the committed descriptor set is compared against the vendored `pg_query.proto` at the pinned libpg_query
  version
- **THEN** the message and field definitions correspond, so parse results from the native library deserialize correctly

### Requirement: Isolated descriptor pool

The `pg_query_pb2` module SHALL register its descriptors in a private `DescriptorPool` rather than the default pool, and
SHALL expose that pool as `pg_query_pb2.DESCRIPTOR_POOL`. Importing postgast SHALL NOT add `pg_query.proto` to the
default descriptor pool, so that postgast can coexist with any other package that registers the same schema.

#### Scenario: Default pool is left untouched

- **WHEN** `postgast` is imported
- **THEN** `descriptor_pool.Default()` does not contain a file named `pg_query.proto`

#### Scenario: Coexists with another registration of the same schema

- **WHEN** another module registers its own `pg_query.proto` in the default pool in the same process
- **THEN** importing postgast succeeds without a duplicate-file conflict

#### Scenario: Pool is reachable for advanced callers

- **WHEN** user code needs descriptor lookup by fully-qualified name
- **THEN** `pg_query_pb2.DESCRIPTOR_POOL.FindMessageTypeByName("pg_query.Node")` resolves

#### Scenario: Wire compatibility across pools

- **WHEN** a message built from postgast's pool is serialized and parsed by a class built from a different pool for the
  same schema
- **THEN** the field values round-trip identically
