## 1. Descriptor set generation

- [x] 1.1 Update the `proto` target in `Makefile` to run
  `protoc --descriptor_set_out=src/postgast/pg_query.desc --include_imports --pyi_out=src/postgast --proto_path=vendor/libpg_query/protobuf pg_query.proto`,
  dropping `--python_out`
- [x] 1.2 Run `make proto` against the vendored `pg_query.proto` and commit `src/postgast/pg_query.desc`
- [x] 1.3 Confirm `pg_query_pb2.pyi` is byte-identical to the committed version after regeneration (the `--pyi_out` path
  is unchanged)
- [x] 1.4 Mark `src/postgast/pg_query.desc` as binary in `.gitattributes` and remove the `linguist-generated=true` line
  for `src/postgast/pg_query_pb2.py`, keeping it for the `.pyi`

## 2. Runtime loader

- [x] 2.1 Replace `src/postgast/pg_query_pb2.py` with a hand-written loader that reads `pg_query.desc` via
  `importlib.resources` and parses it as a `FileDescriptorSet`
- [x] 2.2 Build into a private `descriptor_pool.DescriptorPool()`, adding every file in the set in order; expose the
  pool as `DESCRIPTOR_POOL` and the primary file descriptor as `DESCRIPTOR`
- [x] 2.3 Publish every top-level message as a module attribute via `message_factory.GetMessageClass`
- [x] 2.4 Publish every top-level enum as an `enum_type_wrapper.EnumTypeWrapper`, plus each enum value as a module-level
  integer constant (required by `precedence.py` and `format/constants.py`, and declared by the `.pyi`)
- [x] 2.5 Give the module a docstring explaining that it is hand-written, that `pg_query.desc` is the generated input,
  and that avoiding gencode is what keeps it free of the protobuf runtime version gate

## 3. Dependency and tooling metadata

- [x] 3.1 Change the runtime dependency in `pyproject.toml` from `protobuf>=5.27.2` to `protobuf>=5.29`
- [x] 3.2 Replace `protobuf>=5.27.2,<6.0.0` in the `test` dependency group with `protobuf>=5.29` (both bounds were
  wrong). A `psycopg[binary]>=3.2` lower bound was briefly added here too, because whole-environment
  `--resolution lowest-direct` resolved `psycopg-binary==3.0` and failed to install. That bound has been removed again:
  it described no real requirement of postgast's, and scoping the floor leg's resolution to protobuf (task 5.2) removed
  the need for it. Declaring an unverified floor is the same class of bug this change exists to fix.
- [x] 3.3 Remove `src/postgast/pg_query_pb2.py` from the ruff `exclude`, basedpyright `exclude`, codespell `skip`, and
  coverage `omit` lists, keeping the `.pyi` on each
- [x] 3.4 Run `make lint` and resolve any BasedPyright findings on the loader; if the `globals()` assignments cannot be
  satisfied cleanly, restore the basedpyright exclude only and note why in the module docstring. The fallback was not
  needed — the `globals()` assignments type-check as-is; the only finding was the untyped `DescriptorPool.Add` return,
  handled with a `cast` plus a narrow `# pyright: ignore`.

## 4. Tests

- [x] 4.1 Add a name-parity test that walks `DESCRIPTOR` and asserts a module attribute exists for every top-level
  message, every top-level enum, and every enum value name
- [x] 4.2 Add a test asserting module-level enum constants resolve to the right numbers (e.g. `pb.AEXPR_OP`,
  `pb.SORTBY_ASC`, `pb.AT_AddColumn`) and that the enum wrapper round-trips `Name()`/`Value()`
- [x] 4.3 Add a test that nested types on `SummaryResult` are reachable (`SummaryResult.Table`, `SummaryResult.Context`)
- [x] 4.4 Add a test that `DESCRIPTOR_POOL` is not `descriptor_pool.Default()` and that `pg_query.proto` is absent from
  the default pool after importing postgast
- [x] 4.5 Add a test that a `ParseResult` built by the loader serializes to bytes that parse back with identical field
  values, and that `parse()` on real SQL still returns the expected tree
- [x] 4.6 Run `make generate-nodes` and confirm `src/postgast/nodes/` is unchanged, proving `scripts/generate_nodes.py`
  still walks the descriptor correctly. Verified by generating under the loader and under the old gencode and diffing:
  byte-identical.
- [x] 4.7 Run the full suite on the declared floor (`uv run --with 'protobuf==5.29.1' pytest`) and on the latest
  protobuf, and confirm both pass. Run through the CI commands themselves: the floor leg resolved protobuf 5.29.1 and
  the latest leg 7.36.0; 1047 tests passed on each.

## 5. CI guard

- [x] 5.1 Add a `protobuf-compat` job to `.github/workflows/ci.yml` that runs the test suite twice on Linux — once
  against the declared floor, once against the latest protobuf release
- [x] 5.2 Resolve the floor leg by reading the protobuf specifier out of `pyproject.toml` and installing it with
  `uv pip install --resolution lowest-direct`, and the latest leg with `uv pip install --upgrade protobuf`, so neither
  version is written literally into the workflow, both track `pyproject.toml`, and only protobuf moves. An earlier
  implementation applied `--resolution lowest-direct` to the whole environment; that made a red floor leg ambiguous
  between protobuf and any other dependency's floor, and it required inventing a `psycopg[binary]>=3.2` bound (see 3.2)
  purely to keep the resolution installable. Both are fixed by scoping the resolution to protobuf.
- [x] 5.3 Print the resolved protobuf version at the start of each leg so a failure names the version that produced it
- [x] 5.4 Leave the latest leg unpinned and not `continue-on-error` — a protobuf release breaking postgast is the signal
  the job exists to raise

## 6. Documentation

- [x] 6.1 Note in `README.md` that postgast works across protobuf major versions and does not require protoc
- [x] 6.2 Update the `## cibuildwheel Test Dependencies` guidance in `AGENTS.md` only if the test-requires list changes
  (it should not — protobuf arrives as a core dependency). No change needed: the new tests import only the standard
  library, protobuf, and postgast.
