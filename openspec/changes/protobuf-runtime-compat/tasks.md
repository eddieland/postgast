## 1. Descriptor set generation

- [ ] 1.1 Update the `proto` target in `Makefile` to run
  `protoc --descriptor_set_out=src/postgast/pg_query.desc --include_imports --pyi_out=src/postgast --proto_path=vendor/libpg_query/protobuf pg_query.proto`,
  dropping `--python_out`
- [ ] 1.2 Run `make proto` against the vendored `pg_query.proto` and commit `src/postgast/pg_query.desc`
- [ ] 1.3 Confirm `pg_query_pb2.pyi` is byte-identical to the committed version after regeneration (the `--pyi_out` path
  is unchanged)
- [ ] 1.4 Mark `src/postgast/pg_query.desc` as binary in `.gitattributes` and remove the `linguist-generated=true` line
  for `src/postgast/pg_query_pb2.py`, keeping it for the `.pyi`

## 2. Runtime loader

- [ ] 2.1 Replace `src/postgast/pg_query_pb2.py` with a hand-written loader that reads `pg_query.desc` via
  `importlib.resources` and parses it as a `FileDescriptorSet`
- [ ] 2.2 Build into a private `descriptor_pool.DescriptorPool()`, adding every file in the set in order; expose the
  pool as `DESCRIPTOR_POOL` and the primary file descriptor as `DESCRIPTOR`
- [ ] 2.3 Publish every top-level message as a module attribute via `message_factory.GetMessageClass`
- [ ] 2.4 Publish every top-level enum as an `enum_type_wrapper.EnumTypeWrapper`, plus each enum value as a module-level
  integer constant (required by `precedence.py` and `format/constants.py`, and declared by the `.pyi`)
- [ ] 2.5 Give the module a docstring explaining that it is hand-written, that `pg_query.desc` is the generated input,
  and that avoiding gencode is what keeps it free of the protobuf runtime version gate

## 3. Dependency and tooling metadata

- [ ] 3.1 Change the runtime dependency in `pyproject.toml` from `protobuf>=5.27.2` to `protobuf>=5.29`
- [ ] 3.2 Replace `protobuf>=5.27.2,<6.0.0` in the `test` dependency group with `protobuf>=5.29` (both bounds were
  wrong)
- [ ] 3.3 Remove `src/postgast/pg_query_pb2.py` from the ruff `exclude`, basedpyright `exclude`, codespell `skip`, and
  coverage `omit` lists, keeping the `.pyi` on each
- [ ] 3.4 Run `make lint` and resolve any BasedPyright findings on the loader; if the `globals()` assignments cannot be
  satisfied cleanly, restore the basedpyright exclude only and note why in the module docstring

## 4. Tests

- [ ] 4.1 Add a name-parity test that walks `DESCRIPTOR` and asserts a module attribute exists for every top-level
  message, every top-level enum, and every enum value name
- [ ] 4.2 Add a test asserting module-level enum constants resolve to the right numbers (e.g. `pb.AEXPR_OP`,
  `pb.SORTBY_ASC`, `pb.AT_AddColumn`) and that the enum wrapper round-trips `Name()`/`Value()`
- [ ] 4.3 Add a test that nested types on `SummaryResult` are reachable (`SummaryResult.Table`, `SummaryResult.Context`)
- [ ] 4.4 Add a test that `DESCRIPTOR_POOL` is not `descriptor_pool.Default()` and that `pg_query.proto` is absent from
  the default pool after importing postgast
- [ ] 4.5 Add a test that a `ParseResult` built by the loader serializes to bytes that parse back with identical field
  values, and that `parse()` on real SQL still returns the expected tree
- [ ] 4.6 Run `make generate-nodes` and confirm `src/postgast/nodes/` is unchanged, proving `scripts/generate_nodes.py`
  still walks the descriptor correctly
- [ ] 4.7 Run the full suite on the declared floor (`uv run --with 'protobuf==5.29.1' pytest`) and on the latest
  protobuf, and confirm both pass

## 5. CI guard

- [ ] 5.1 Add a `protobuf-compat` job to `.github/workflows/ci.yml` that runs the test suite twice on Linux — once with
  protobuf pinned to the declared floor, once with the latest release
- [ ] 5.2 Have the job install the floor from the `dependencies` declaration rather than a hardcoded literal, so the job
  fails if the declared floor stops working

## 6. Documentation

- [ ] 6.1 Note in `README.md` that postgast works across protobuf major versions and does not require protoc
- [ ] 6.2 Update the `## cibuildwheel Test Dependencies` guidance in `AGENTS.md` only if the test-requires list changes
  (it should not — protobuf arrives as a core dependency)
