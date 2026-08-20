## Context

`src/postgast/pg_query_pb2.py` is protoc output committed to the repository so that source installs do not need protoc
(`openspec/specs/bindings/spec.md`). Since protobuf 5.27, that output opens with a version gate:

```python
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 0, "", "pg_query.proto")
```

The public rule the gate enforces is one-directional — the runtime may not be *older* than the gencode. Measured on the
committed file:

| protobuf runtime | result                            |
| ---------------- | --------------------------------- |
| 5.27.2           | `VersionError` at import          |
| 5.28.3           | `VersionError` at import          |
| 5.29.0           | ok (release is yanked)            |
| 5.29.6           | ok                                |
| 7.35.1           | ok, no warning, correct roundtrip |

`runtime_version.py` in 7.35.1 contains no gencode-too-old branch at all, only the runtime-older check, so newer majors
are not the hazard. The hazard is the declared floor of `>=5.27.2`, which permits runtimes that cannot load the file.

postgast never needs gencode semantics. It parses bytes produced by libpg_query's protobuf-c encoder and hands back
message objects; the C side owns the wire format, and the Python side only needs classes matching the vendored schema.
Message classes can be built from a serialized descriptor with public runtime APIs, which no version gate covers.

## Goals / Non-Goals

**Goals:**

- Make `import postgast` succeed on every protobuf runtime the package declares, and stop coupling releases to the
  protoc version used to build them.
- Preserve the public surface of `postgast.pg_query_pb2` exactly — it is exported in `__all__` and used across
  `precedence.py`, `format/`, `helpers.py`, `parse.py`, and the generated node wrappers.
- Keep static typing intact via the existing `pg_query_pb2.pyi`.

**Non-Goals:**

- Letting users bring their own protoc. Wheels are prebuilt, so build-time generation would reach almost no one, pip
  build isolation resolves the build-time protobuf separately from the runtime one, and a user-supplied schema that does
  not match the vendored libpg_query version drifts field numbers into silent misparses.
- Lowering the floor below 5.29. Dynamic building would allow it (`message_factory.GetMessageClass` has existed since
  4.22), but there is no demand and it widens the support matrix for nothing.
- Changing how libpg_query is vendored, built, or invoked.

## Decisions

### Build message classes at import from a committed descriptor set

`pg_query_pb2.py` becomes hand-written and does the work protoc gencode does, minus the gate:

```python
_pool = descriptor_pool.DescriptorPool()
_fds = descriptor_pb2.FileDescriptorSet()
_fds.ParseFromString(_DESCRIPTOR_BYTES)
for _file in _fds.file:  # topologically ordered by --include_imports
    DESCRIPTOR = _pool.Add(_file)
for _name, _desc in DESCRIPTOR.message_types_by_name.items():
    globals()[_name] = message_factory.GetMessageClass(_desc)
for _name, _desc in DESCRIPTOR.enum_types_by_name.items():
    globals()[_name] = enum_type_wrapper.EnumTypeWrapper(_desc)
    for _value in _desc.values:
        globals()[_value.name] = _value.number
```

`descriptor_pool`, `descriptor_pb2`, `message_factory.GetMessageClass`, and `enum_type_wrapper` are all public API.
Gencode instead calls `google.protobuf.internal.builder`, which is explicitly internal — so the loader depends on a
*more* stable surface than the file it replaces.

The third loop matters: `precedence.py` and `format/constants.py` use module-level enum constants heavily
(`pb.AEXPR_OP`, `pb.AT_AddColumn`, `pb.SORTBY_ASC`), and `pg_query_pb2.pyi` declares 1082 of them at module level. A
prototype of the loader above was compared against the current gencode by exported-name set: **1432 names on each side,
empty difference, on both protobuf 5.29.6 and 7.35.1.** The schema has no extensions and no services, so nothing else
needs publishing. `SummaryResult` is the only message with nested types; `GetMessageClass` attaches those to the class
(`SummaryResult.Table`, `SummaryResult.Context`), matching gencode.

**Why not simply strip the `ValidateProtobufRuntimeVersion` call from the generated file?** It reaches the same place in
one `sed`, but leaves `make proto` post-processing protoc output — a step that breaks silently whenever protoc changes
its preamble, and one that has to be re-verified on every libpg_query bump.

### Ship the descriptor as `pg_query.desc`, not an embedded bytes literal

`make proto` gains `--descriptor_set_out=src/postgast/pg_query.desc --include_imports` and drops `--python_out`. The
alternative — a generated module holding the descriptor as a `bytes` literal — needs a wrapper script to produce it,
whereas a descriptor set is a first-class protoc output. Hatchling already ships non-Python files inside
`packages = ["src/postgast"]` (this is how `py.typed` reaches the wheel), and the sdist include list covers
`src/postgast`, so no packaging changes are needed.

`--include_imports` is defensive: `pg_query.proto` currently imports nothing, but if upstream ever adds an import, the
set stays self-contained and the loader's `for _file in _fds.file` loop adds dependencies before dependents.

### Use a private descriptor pool

Gencode always registers in the default pool, so a process where any other package registers `pg_query.proto` — a user's
own protoc output for the same schema, most plausibly — dies at import with a duplicate-file error. A private pool
removes that failure mode. The schema imports nothing, so it needs no symbols from the default pool.

The trade-off is that `descriptor_pool.Default().FindMessageTypeByName("pg_query.Node")` stops resolving. That is an
unusual thing to depend on, and the pool is exposed as `pg_query_pb2.DESCRIPTOR_POOL` for anyone who does. Wire
compatibility is unaffected: a message built in the private pool serializes to bytes that a default-pool class parses
back identically (verified).

### Correct the floor to `protobuf>=5.29`, no upper bound

This matches what `openspec/specs/bindings/spec.md` already requires and what actually imports. The `test` group's
`protobuf>=5.27.2,<6.0.0` pin loses both bounds: the lower one is wrong, and the upper one guards a break that does not
occur on 7.35.1. A CI job pinning the floor exactly, plus one tracking the latest release, keeps the declared range
honest — the current mismatch survived precisely because nothing ever installed the floor.

### Type checking and linting

`pg_query_pb2.pyi` is unchanged and still generated by `--pyi_out`, so type checkers see the same surface they see
today; a `.pyi` takes precedence over its `.py` for every importer regardless of how the module builds itself. Now that
the `.py` is hand-written and short, it comes off the ruff, basedpyright, codespell, and coverage exclude lists — the
`.pyi` stays on them. The `globals()` assignments may need a narrow `# type: ignore` for BasedPyright; if that turns
into a fight, keeping the `.py` excluded is an acceptable fallback, since the stub is what callers are checked against.

## Risks / Trade-offs

- [Silent surface drift] A future libpg_query bump could change the schema in a way the loader publishes differently
  from gencode, and no protoc-generated `.py` will exist to diff against. Mitigated by a test that walks `DESCRIPTOR`
  and asserts a module attribute exists for every message, enum, and enum value — the same invariant, checked from the
  descriptor rather than from a golden file.
- [Import-time cost] Class construction moves from `.pyc` loading to descriptor walking. Measured at 5.5 ms versus 4.9
  ms for the gencode import plus first message construction — within noise, and both are dwarfed by loading the native
  library.
- [Private pool visibility] Covered above: `DESCRIPTOR_POOL` is exported for the rare caller that needs pool access, and
  the case it breaks is one that currently crashes at import anyway.
- \[Loss of `linguist-generated`\] `pg_query_pb2.py` starts appearing in diffs and language statistics. That is correct
  — it becomes real source — and it is ~40 lines rather than ~100 KB.
