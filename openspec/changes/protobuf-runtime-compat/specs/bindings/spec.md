## MODIFIED Requirements

### Requirement: Protobuf runtime dependency

The package SHALL declare `protobuf>=5.29` as a runtime dependency in `pyproject.toml` `dependencies`, with no upper
version bound. This is the official Google protobuf library.

The declared floor SHALL be greater than or equal to the gencode version stamped in `src/postgast/pg_query_pb2.py`,
since protobuf's cross-version guarantee is one-directional: the runtime may not be older than the gencode that a module
was generated from. Whenever `make proto` regenerates the module with a newer protoc, the declared floor SHALL be raised
to match the new stamp.

No upper bound SHALL be declared, in `dependencies` or in the `test` dependency group. The version gate has no
gencode-too-old branch, so a protobuf major newer than the generating protoc is not a compatibility hazard.

#### Scenario: Dependency is installed automatically

- **WHEN** a user runs `pip install postgast`
- **THEN** the `protobuf` package is installed as a dependency

#### Scenario: Declared floor is importable

- **WHEN** the lowest protobuf version permitted by `dependencies` is installed
- **THEN** `import postgast` succeeds and message classes are usable

#### Scenario: Floor is not older than the gencode stamp

- **WHEN** the floor declared in `dependencies` is compared against the `Protobuf Python Version` stamp in
  `pg_query_pb2.py`
- **THEN** the floor is greater than or equal to the stamped version

#### Scenario: No upper bound blocks new majors

- **WHEN** a protobuf release with a newer major version than the one used during development is installed
- **THEN** the dependency declaration permits it, and `import postgast` succeeds with no error and no version warning
