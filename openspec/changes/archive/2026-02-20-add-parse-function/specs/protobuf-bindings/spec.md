## ADDED Requirements

### Requirement: Generated protobuf module

The package SHALL include a generated Python protobuf module (`_pg_query_pb2.py`) produced by running `protoc` against
the vendored `vendor/libpg_query/protobuf/pg_query.proto`. The generated file SHALL be committed to the repository so
that users installing from source do not need `protoc`.

#### Scenario: Module is importable

- **WHEN** the package is installed
- **THEN** `from postgast._pg_query_pb2 import ParseResult` succeeds without error

#### Scenario: ParseResult message structure

- **WHEN** the `ParseResult` message is inspected
- **THEN** it has an `int32 version` field and a `repeated RawStmt stmts` field matching the proto schema

### Requirement: Protobuf runtime dependency

The package SHALL declare `protobuf>=5.29` as a runtime dependency in `pyproject.toml` `dependencies`. This is the
official Google protobuf library.

#### Scenario: Dependency is installed automatically

- **WHEN** a user runs `pip install postgast`
- **THEN** the `protobuf` package is installed as a dependency

### Requirement: Makefile regeneration target

The project SHALL provide a `make proto` target that regenerates `_pg_query_pb2.py` from the vendored proto file. This
target is used by maintainers when the vendored `pg_query.proto` is updated.

#### Scenario: Regeneration produces identical output

- **WHEN** `make proto` is run without modifying the vendored proto file
- **THEN** the generated `_pg_query_pb2.py` is byte-identical to the committed version

#### Scenario: Regeneration reflects proto changes

- **WHEN** the vendored `pg_query.proto` is updated and `make proto` is run
- **THEN** the generated `_pg_query_pb2.py` reflects the updated proto definitions

### Requirement: Protobuf module re-export

The generated protobuf module SHALL be re-exported from the `postgast` package as `postgast.pg_query_pb2` so users can
access AST node types (e.g., `from postgast.pg_query_pb2 import ParseResult, Node, SelectStmt`).

#### Scenario: Public re-export access

- **WHEN** user code runs `from postgast import pg_query_pb2`
- **THEN** the module is accessible and contains protobuf message classes
