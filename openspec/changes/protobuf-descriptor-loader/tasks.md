## 0. Prerequisite decision

- [ ] 0.1 Decide the target floor. If the answer is "stay at 5.29", close this change — it produces an identical support
  matrix for a hand-written module plus a binary artifact. Everything below assumes the floor is being lowered.
- [ ] 0.2 Confirm `protobuf-runtime-compat` has landed, so the `protobuf-compat` CI job exists to verify the new floor

## 1. Descriptor set generation

- [ ] 1.1 Update the `proto` target in `Makefile` to run
  `protoc --descriptor_set_out=src/postgast/pg_query.desc --include_imports --pyi_out=src/postgast --proto_path=vendor/libpg_query/protobuf pg_query.proto`,
  dropping `--python_out`
- [ ] 1.2 Run `make proto` against the vendored `pg_query.proto` and commit `src/postgast/pg_query.desc`
- [ ] 1.3 Confirm `pg_query_pb2.pyi` is byte-identical to the committed version after regeneration
- [ ] 1.4 Mark `src/postgast/pg_query.desc` as binary in `.gitattributes` and remove the `linguist-generated=true` line
  for `src/postgast/pg_query_pb2.py`, keeping it for the `.pyi`

## 2. Runtime loader

- [ ] 2.1 Replace `src/postgast/pg_query_pb2.py` with a hand-written loader that reads `pg_query.desc` via
  `Path(__file__).with_name(...)` — **not** `importlib.resources`, which imports the `postgast` package and breaks
  `make generate-nodes` before the native library is built (see `design.md`)
- [ ] 2.2 Build into a private `descriptor_pool.DescriptorPool()`, adding every file in the set in order; expose the
  pool as `DESCRIPTOR_POOL`, and obtain `DESCRIPTOR` via `FindFileByName` — **not** from the return value of
  `pool.Add()`, which is `None` on the pure-Python backend
- [ ] 2.3 Publish every top-level message as a module attribute via `message_factory.GetMessageClass`, setting
  `__module__` on each class so messages remain picklable
- [ ] 2.4 Publish every top-level enum as an `enum_type_wrapper.EnumTypeWrapper`, plus each enum value as a module-level
  integer constant (required by `precedence.py` and `format/constants.py`, and declared by the `.pyi`)
- [ ] 2.5 Give the module a docstring explaining that it is hand-written, that `pg_query.desc` is the generated input,
  and that avoiding gencode is what keeps it free of the protobuf runtime version gate

## 3. Dependency and tooling metadata

- [ ] 3.1 Lower the runtime floor in `pyproject.toml` to the decided version and update the `test` group to match
- [ ] 3.2 Update the `bindings` spec's floor requirement and run `uv lock`
- [ ] 3.3 Remove `src/postgast/pg_query_pb2.py` from the ruff `exclude`, codespell `skip`, and coverage `omit` lists,
  keeping the `.pyi` on each
- [ ] 3.4 Run `make lint` and resolve any BasedPyright findings on the loader; if the `globals()` assignments cannot be
  satisfied cleanly, restore the basedpyright exclude only and note why in the module docstring

## 4. Tests

- [ ] 4.1 Add a name-parity test that walks `DESCRIPTOR` and asserts a module attribute exists for every top-level
  message, every top-level enum, and every enum value name
- [ ] 4.2 Add a test asserting module-level enum constants resolve to the right numbers (e.g. `pb.AEXPR_OP`,
  `pb.SORTBY_ASC`, `pb.AT_AddColumn`) and that the enum wrapper round-trips `Name()`/`Value()`
- [ ] 4.3 Add a test that nested types on `SummaryResult` are reachable — `SummaryResult.Table`,
  `SummaryResult.Function`, `SummaryResult.FilterColumn`, and the nested enum `SummaryResult.Context`
- [ ] 4.4 Add a test that `DESCRIPTOR_POOL` is not `descriptor_pool.Default()` and that `pg_query.proto` is absent from
  the default pool after importing postgast
- [ ] 4.5 Add a behavioural surface test — messages pickle and deepcopy round-trip, and `type(m).__module__` is
  `postgast.pg_query_pb2` — since name-set comparison alone does not prove surface parity
- [ ] 4.6 Add a test that a `ParseResult` built by the loader serializes to bytes that parse back with identical field
  values, and that `parse()` on real SQL still returns the expected tree
- [ ] 4.7 Run `make generate-nodes` **with the native library absent** and confirm `src/postgast/nodes/` is unchanged,
  proving the bootstrap path still works
- [ ] 4.8 Run the full suite under `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` as well as the default upb backend
- [ ] 4.9 Run the full suite on the new floor and on the latest protobuf, and confirm both pass
