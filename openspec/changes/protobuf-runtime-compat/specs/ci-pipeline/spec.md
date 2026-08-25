## ADDED Requirements

### Requirement: Protobuf version compatibility job

The CI workflow SHALL include a `protobuf-compat` job that runs the test suite against both ends of the declared
protobuf range: the lowest installable version permitted by `pyproject.toml` `dependencies`, and the latest published
protobuf release.

Neither version SHALL be written literally into the workflow. The job SHALL read the protobuf specifier from
`pyproject.toml` `dependencies` at run time, so that changing the declared floor changes what the job exercises with no
edit to the workflow.

The job SHALL move only the protobuf version, leaving every other dependency resolved as the `test` job resolves it, so
that a failure in either leg names protobuf rather than an unrelated dependency floor. The floor leg SHALL resolve
downward from the extracted specifier (`uv pip install --resolution lowest-direct`); the latest leg SHALL resolve upward
with no upper constraint (`uv pip install --upgrade protobuf`). Both legs SHALL print the resolved protobuf version
before running the suite.

The latest leg is deliberately unpinned and is therefore not reproducible across time: a newly published protobuf
release may turn it red with no change to the repository. That is the intended signal — an early warning that a protobuf
release broke postgast — and SHALL NOT be suppressed by pinning the version. It SHALL NOT be marked `continue-on-error`,
since a silent canary defeats the purpose.

#### Scenario: Floor is exercised

- **WHEN** the compatibility job runs its floor leg
- **THEN** it resolves the lowest installable protobuf version permitted by `dependencies`, prints it, and the test
  suite passes

#### Scenario: Latest release is exercised

- **WHEN** the compatibility job runs its latest leg
- **THEN** it resolves the newest published protobuf release compatible with the job's Python version, prints it, and
  the test suite passes

#### Scenario: Neither version is hardcoded

- **WHEN** the protobuf floor in `pyproject.toml` `dependencies` is changed
- **THEN** the compatibility job exercises the new floor without any edit to the workflow file

#### Scenario: Only protobuf is moved

- **WHEN** either leg resolves its protobuf version
- **THEN** the remaining dependencies are left at the versions the `test` job resolves, so neither leg reports a failure
  caused by an unrelated dependency floor

#### Scenario: Mismatched floor fails CI

- **WHEN** the declared floor is lower than the protobuf version required to import `pg_query_pb2`
- **THEN** the floor leg fails

#### Scenario: A breaking protobuf release fails CI

- **WHEN** a newly published protobuf release cannot load the committed protobuf module
- **THEN** the latest leg fails rather than being skipped or downgraded to a warning

#### Scenario: Job runs on a single OS

- **WHEN** the compatibility job is scheduled
- **THEN** it runs on Linux only, since protobuf runtime compatibility is not platform-dependent
