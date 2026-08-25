## Context

`src/postgast/pg_query_pb2.py` is protoc output committed to the repository so that source installs do not need protoc
(`openspec/specs/bindings/spec.md`). Since protobuf 5.27, that output opens with a version gate:

```python
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 0, "", "pg_query.proto")
```

The rule it enforces is one-directional — the runtime may not be *older* than the gencode. There is no gencode-too-old
branch in `runtime_version.py`, which is why new majors pass and the declared floor is the only real exposure.

## Goals / Non-Goals

**Goals:**

- Make the declared protobuf range describe the range that actually works, at both ends.
- Make CI fail the next time the two drift, rather than letting a release ship broken.

**Non-Goals:**

- Replacing gencode. A descriptor-set loader would remove the gate entirely and allow a floor near 4.25, but it is a
  much larger change and it does not fix anything this change does not. Deferred to
  `openspec/changes/protobuf-descriptor-loader/`.
- Lowering the floor below 5.29. Nothing asks for it while gencode remains.
- Changing how libpg_query is vendored, built, or invoked.

## Decisions

### Correct the floor to `protobuf>=5.29`, no upper bound

This matches what `openspec/specs/bindings/spec.md` already requires and what actually imports. The `test` group's
`protobuf>=5.27.2,<6.0.0` loses both bounds: the lower one is wrong, and the upper one guards a break that does not
occur on 6.33.1 or 7.36.0.

The floor is stated as `>=5.29` rather than `>=5.29.1` because 5.29.0 is what the gencode stamp actually requires and it
does import correctly. 5.29.0 was yanked, so no resolver will select it unless a user pins it exactly; CI therefore
exercises 5.29.1 as the lowest *installable* version in the declared range. That one-version gap is intentional and
harmless — the yanked release works, it is just unreachable.

### Move only protobuf in the compatibility job

The obvious way to reach the floor is `uv run --resolution lowest-direct`, but that lowers *every* direct dependency —
pytest, hypothesis, ruamel — so a red floor leg would no longer mean "the protobuf floor broke". The job pins protobuf
alone, on top of a normally-resolved environment:

```
uv pip install --resolution lowest-direct "$(extracted specifier from pyproject.toml)"   # floor leg
uv pip install --upgrade protobuf                                                        # latest leg
```

Verified: against `protobuf>=5.29` the first resolves to 5.29.1 (skipping the yanked 5.29.0) and the second to 7.36.0.
The specifier is read out of `pyproject.toml` at run time, so changing the floor changes what CI tests with no edit to
the workflow.

The job needs the native library, so it reuses the `test` job's `make build-native` step and runs on Linux only —
protobuf runtime compatibility is not platform-dependent.

### Leave the latest leg unpinned and blocking

A newly published protobuf release can turn the job red with no change to the repository. That is the signal the job
exists to raise, so it is neither pinned nor `continue-on-error`. A silent canary is not a canary.

## Risks / Trade-offs

- [Unpinned latest leg is not reproducible across time] Accepted, and the point — see above. The floor leg and the main
  `test` matrix are both reproducible, so a red latest leg is unambiguous about what changed.
- [The floor stays coupled to protoc] Every `make proto` on a newer protoc raises the required floor again. This change
  does not remove that coupling, it only makes it loud. Removing it is the deferred loader proposal.
- [CI does not exercise 5.29.0 exactly] Covered above: yanked, unreachable by resolvers, verified working by hand.
