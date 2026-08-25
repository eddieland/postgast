## 1. Dependency metadata

- [ ] 1.1 Change the runtime dependency in `pyproject.toml` from `protobuf>=5.27.2` to `protobuf>=5.29`
- [ ] 1.2 Replace `protobuf>=5.27.2,<6.0.0` in the `test` dependency group with `protobuf>=5.29`, dropping the stale
  "pin to avoid regenerating pb2" comment
- [ ] 1.3 Run `uv lock` and commit the regenerated `uv.lock`

## 2. Tests

- [ ] 2.1 Add `tests/postgast/test_protobuf_bindings.py` with a test that reads the `Protobuf Python Version:` stamp
  from `pg_query_pb2.py` and asserts the floor declared in `pyproject.toml` `dependencies` is greater than or equal to
  it — the invariant that was violated, checked from the two files that must agree
- [ ] 2.2 Add a test that the installed protobuf runtime satisfies the declared floor, so a developer running the suite
  on a too-old runtime gets a named failure rather than a collection error
- [ ] 2.3 Run the suite against the floor (`uv run --isolated --with 'protobuf==5.29.1' pytest`) and against the latest
  release, and confirm both pass

## 3. CI guard

- [ ] 3.1 Add a `protobuf-compat` job to `.github/workflows/ci.yml`: `needs: lint`, `runs-on: ubuntu-latest`, a
  two-entry matrix (`leg: [floor, latest]`), reusing the `test` job's checkout, uv setup, `uv sync`, and
  `make build-native` steps
- [ ] 3.2 Extract the protobuf specifier from `pyproject.toml` `dependencies` at run time (stdlib `tomllib`) rather than
  writing a version into the workflow
- [ ] 3.3 Resolve the floor leg with `uv pip install --resolution lowest-direct "<extracted specifier>"` and the latest
  leg with `uv pip install --upgrade protobuf`, so only protobuf moves and the rest of the environment stays as the
  `test` job resolves it
- [ ] 3.4 Print the resolved protobuf version before running the suite so a failure names the version that produced it
- [ ] 3.5 Run the suite with `uv run --no-sync pytest` so the leg's pinned protobuf is not re-resolved away
- [ ] 3.6 Leave the latest leg unpinned and not `continue-on-error`
- [ ] 3.7 Confirm the floor leg fails as expected by temporarily setting the floor below 5.29 locally, then revert

## 4. Documentation

- [ ] 4.1 Note in `README.md` that postgast supports protobuf 5.29 and later, including protobuf 6 and 7
