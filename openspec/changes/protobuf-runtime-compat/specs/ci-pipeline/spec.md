## ADDED Requirements

### Requirement: Protobuf version compatibility job

The CI workflow SHALL include a job that runs the test suite against both ends of the declared protobuf range: the exact
floor named in `pyproject.toml` `dependencies`, and the latest published protobuf release. The floor SHALL be derived
from the dependency declaration rather than hardcoded in the workflow, so that a floor which no longer imports fails CI.

#### Scenario: Floor is exercised

- **WHEN** the compatibility job runs
- **THEN** it installs the exact minimum protobuf version permitted by `dependencies` and the test suite passes

#### Scenario: Latest release is exercised

- **WHEN** the compatibility job runs
- **THEN** it installs the latest published protobuf release and the test suite passes

#### Scenario: Mismatched floor fails CI

- **WHEN** the declared floor is lower than the protobuf version required to import `pg_query_pb2`
- **THEN** the compatibility job fails

#### Scenario: Job runs on a single OS

- **WHEN** the compatibility job is scheduled
- **THEN** it runs on Linux only, since protobuf runtime compatibility is not platform-dependent
