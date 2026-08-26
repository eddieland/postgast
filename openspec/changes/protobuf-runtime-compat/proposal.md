## Why

`pyproject.toml` declares `protobuf>=5.27.2`, but `src/postgast/pg_query_pb2.py` is protoc gencode stamped
`Protobuf Python Version: 5.29.0`. Protobuf's only cross-version guarantee is *runtime >= gencode*, so every runtime the
resolver may legally pick in `[5.27.2, 5.29.0)` fails at import:

```
VersionError: Detected incompatible Protobuf Gencode/Runtime versions when loading pg_query.proto:
gencode 5.29.0 runtime 5.27.2. Runtime version cannot be older than the linked gencode version.
```

Verified against the committed gencode:

| protobuf runtime | result                   |
| ---------------- | ------------------------ |
| 5.27.2           | `VersionError` at import |
| 5.28.3           | `VersionError` at import |
| 5.29.1           | imports, messages usable |
| 6.33.1           | imports, no warning      |
| 7.36.0           | imports, no warning      |

`openspec/specs/bindings/spec.md` already requires `protobuf>=5.29` — `pyproject.toml` is the file that drifted.

The `test` group carries a defensive `protobuf<6.0.0` pin ("pin to avoid regenerating pb2 when protobuf major changes").
That guards a risk that does not exist: the gate is one-directional and `runtime_version.py` has no gencode-too-old
branch, so newer majors are not the hazard. Verified — the same gencode imports and roundtrips cleanly on 6.33.1 and
7.36.0 with warnings raised as errors.

Both bounds are wrong, and both survived because nothing in CI ever installs either end of the declared range.

## What Changes

- Correct the runtime floor in `pyproject.toml` from `protobuf>=5.27.2` to `protobuf>=5.29`, matching what the
  `bindings` spec already requires and what actually imports.
- Drop the `<6.0.0` upper pin from the `test` dependency group.
- Add a CI job that runs the test suite against both ends of the declared range — the floor and the latest release —
  resolving both from `pyproject.toml` so neither is written into the workflow.

Every future `make proto` on a newer protoc silently raises the required floor; that is how this shipped. The CI job is
what turns the next occurrence into a red build instead of a broken release.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `bindings`: The protobuf runtime dependency requirement gains an explicit no-upper-bound statement and scenarios
  asserting that the declared floor is a version which can actually import `pg_query_pb2`.
- `ci-pipeline`: Adds a protobuf version compatibility job covering the declared floor and the latest release.

## Impact

- `pyproject.toml` — `dependencies` floor corrected to `protobuf>=5.29`; `test` group pin becomes `protobuf>=5.29`
- `.github/workflows/ci.yml` — new `protobuf-compat` job
- `tests/postgast/test_protobuf_bindings.py` — extended: asserts the declared floor is consistent with the gencode stamp
  (the file already exists)
- `tests/conftest.py` — new: a `pytest_configure` bootstrap check that names a too-old protobuf runtime before
  `tests/postgast/conftest.py` imports `postgast` and dies at collection
- `uv.lock` — regenerated for the changed constraints

Not in scope: `src/postgast/pg_query_pb2.py`, `Makefile`, `.gitattributes`. Replacing gencode with a descriptor-set
loader is a separate, deferred proposal — see `openspec/changes/protobuf-descriptor-loader/`.
