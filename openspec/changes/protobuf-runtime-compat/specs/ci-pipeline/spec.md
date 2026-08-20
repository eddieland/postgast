## ADDED Requirements

### Requirement: Protobuf version compatibility job

The CI workflow SHALL include a job that runs the test suite against both ends of the declared protobuf range: the exact
floor named in `pyproject.toml` `dependencies`, and the latest published protobuf release. Neither version SHALL be
written literally into the workflow — both SHALL be resolved from the dependency declaration at run time, so that the
job tracks `pyproject.toml` automatically and a floor which no longer imports fails CI.

The floor leg SHALL obtain its version by resolving direct dependencies downward (`uv run --resolution lowest-direct`).
The latest leg SHALL resolve upward with no upper constraint (`uv run --resolution highest --upgrade-package protobuf`).
Both legs SHALL print the resolved protobuf version before running the suite, so a failure names the version that
produced it.

The latest leg is deliberately unpinned and is therefore not reproducible across time: a newly published protobuf
release may turn it red with no change to the repository. That is the intended signal — an early warning that a protobuf
release broke postgast — and SHALL NOT be suppressed by pinning the version. It SHALL NOT be marked `continue-on-error`,
since a silent canary defeats the purpose.

#### Scenario: Floor is exercised

- **WHEN** the compatibility job runs its floor leg
- **THEN** it resolves the exact minimum protobuf version permitted by `dependencies`, prints it, and the test suite
  passes

#### Scenario: Latest release is exercised

- **WHEN** the compatibility job runs its latest leg
- **THEN** it resolves the newest published protobuf release compatible with the job's Python version, prints it, and
  the test suite passes

#### Scenario: Neither version is hardcoded

- **WHEN** the protobuf floor in `pyproject.toml` `dependencies` is changed
- **THEN** the compatibility job exercises the new floor without any edit to the workflow file

#### Scenario: Mismatched floor fails CI

- **WHEN** the declared floor is lower than the protobuf version required to import `pg_query_pb2`
- **THEN** the floor leg fails

#### Scenario: A breaking protobuf release fails CI

- **WHEN** a newly published protobuf release cannot load the committed descriptor set
- **THEN** the latest leg fails rather than being skipped or downgraded to a warning

#### Scenario: Job runs on a single OS

- **WHEN** the compatibility job is scheduled
- **THEN** it runs on Linux only, since protobuf runtime compatibility is not platform-dependent
