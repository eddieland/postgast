## Context

See `proposal.md`. This change is deferred; the material below is the verified groundwork, including several defects
found in an earlier draft that a naive implementation will re-introduce.

`postgast` uses `pg_query_pb2` heavily at module level — `precedence.py` and `format/constants.py` read enum constants
(`pb.AEXPR_OP`, `pb.AT_AddColumn`, `pb.SORTBY_ASC`), `nodes/_generated.py` annotates against message classes, and
`scripts/generate_nodes.py` walks `DESCRIPTOR`. The loader must reproduce that surface exactly.

## Verified facts

Measured against the committed gencode and a prototype loader, on the vendored schema (276 top-level messages, 73
top-level enums, 1082 enum value constants, no extensions, no services):

- **Name parity holds.** 1432 module-level public names on each side, empty difference in both directions, on protobuf
  5.29.6 and 7.35.1.

- **The loader works far below the current floor.** Verified on 4.25.8, 5.27.2, 5.28.3, 5.29.6, 6.33.1 — 1432 names and
  a correct serialize/parse roundtrip on each.

- **`SummaryResult` is the only message with nested types** (`Table`, `AliasesEntry`, `Function`, `FilterColumn`) and
  the only one with a nested enum (`Context`). `message_factory.GetMessageClass` attaches all of them to the class,
  matching gencode.

- **Import cost is higher than an earlier draft claimed.** Cold-process module import, including the protobuf runtime:

  | backend | gencode | loader  |
  | ------- | ------- | ------- |
  | upb     | 33.8 ms | 43.5 ms |
  | python  | 248 ms  | 338 ms  |

  The earlier "5.5 ms vs 4.9 ms, within noise" figure measured only the class-building step, with protobuf already
  imported, on upb only. The conclusion survives — both are dwarfed by loading the native library — but the margin is
  roughly +30%, not noise, and the pure-Python backend was never measured.

## Defects to avoid

Each of these was found in an earlier draft of this change and verified against a live runtime.

### `pool.Add()` does not return a descriptor on every backend

```python
DESCRIPTOR = _pool.Add(_file)  # WRONG
```

```
upb:    pool.Add() -> FileDescriptor
python: pool.Add() -> None
```

Under `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` this silently sets `DESCRIPTOR = None`, breaking
`scripts/generate_nodes.py:632`. Use `AddSerializedFile`, or call `FindFileByName` after the add loop.

### `importlib.resources` breaks `make generate-nodes`

`scripts/generate_nodes.py` loads the module by file path specifically "to avoid triggering postgast.__init__". But
`importlib.resources.files("postgast")` executes that `__init__`, which loads the native library:

```
OSError: libpg_query shared library not found
```

So reading the descriptor via `importlib.resources` breaks node regeneration in exactly the bootstrap case the script
was written for — regenerating before the native library is built. Use `Path(__file__).with_name("pg_query.desc")`.

### Dynamic classes do not pickle

`message_factory.GetMessageClass` leaves `__module__` unset:

```
gencode class __module__ = pg_query_pb2
dynamic class __module__ = None
```

`pickle.dumps(pb.ParseResult(version=170000))` succeeds today and raises `PicklingError` with the loader. That matters
for users caching parse trees or passing messages across `multiprocessing` workers; nothing internal to postgast
pickles. Fix by setting `cls.__module__ = __name__` on each published class — and note that a name-set comparison, the
check an earlier draft relied on to claim an identical public surface, does not catch this. Surface parity needs
behavioural assertions, not just `dir()`.

## Decisions

### Build message classes at import from a committed descriptor set

```python
_pool = descriptor_pool.DescriptorPool()
_fds = descriptor_pb2.FileDescriptorSet()
_fds.ParseFromString(_DESCRIPTOR_BYTES)
for _file in _fds.file:  # topologically ordered by --include_imports
    _pool.Add(_file)
DESCRIPTOR = _pool.FindFileByName("pg_query.proto")
for _name, _desc in DESCRIPTOR.message_types_by_name.items():
    _cls = message_factory.GetMessageClass(_desc)
    _cls.__module__ = __name__
    globals()[_name] = _cls
for _name, _desc in DESCRIPTOR.enum_types_by_name.items():
    globals()[_name] = enum_type_wrapper.EnumTypeWrapper(_desc)
    for _value in _desc.values:
        globals()[_value.name] = _value.number
```

`descriptor_pool`, `descriptor_pb2`, `message_factory.GetMessageClass`, and `enum_type_wrapper` are all public API.
Gencode instead calls `google.protobuf.internal.builder`, which is explicitly internal — so the loader depends on a
*more* stable surface than the file it replaces.

**Why not strip the `ValidateProtobufRuntimeVersion` call from the generated file?** It reaches the same place in one
`sed`, but leaves `make proto` post-processing protoc output — a step that breaks silently whenever protoc changes its
preamble, and one that has to be re-verified on every libpg_query bump.

### Ship the descriptor as `pg_query.desc`, not an embedded bytes literal

`make proto` gains `--descriptor_set_out=src/postgast/pg_query.desc --include_imports` and drops `--python_out`. A
descriptor set is a first-class protoc output; a generated module holding the same bytes as a literal would need a
wrapper script. Hatchling already ships non-Python files inside `packages = ["src/postgast"]` (this is how `py.typed`
reaches the wheel), so no packaging changes are needed.

`--include_imports` is defensive: `pg_query.proto` currently imports nothing, but if upstream ever adds an import, the
set stays self-contained and the add loop handles dependencies before dependents.

Note that the descriptor does not disappear — it moves. The committed gencode is 211 KB, of which roughly half is the
same serialized descriptor as an escaped bytes literal and most of the rest is a table of `_serialized_start/_end`
offsets. The descriptor set is ~102 KB.

### Use a private descriptor pool

Gencode always registers in the default pool, so a process where any other package registers `pg_query.proto` dies at
import with a duplicate-file error. A private pool removes that failure mode. The schema imports nothing, so it needs no
symbols from the default pool.

Two trade-offs, both real:

- `descriptor_pool.Default().FindMessageTypeByName("pg_query.Node")` stops resolving. Unusual to depend on; the pool is
  exposed as `pg_query_pb2.DESCRIPTOR_POOL` for anyone who does.
- The duplicate-registration case changes from a loud import-time crash to silent coexistence, in which messages from
  postgast's pool are not `isinstance` of the other package's classes. Wire compatibility is unaffected — a message
  built in the private pool serializes to bytes a default-pool class parses back identically (verified) — but code doing
  `isinstance` checks across the two would now fail quietly where it previously could not run at all. On balance worth
  it, but it is a trade, not a pure win.

### Type checking and linting

`pg_query_pb2.pyi` is unchanged and still generated by `--pyi_out`, so type checkers see the same surface; a `.pyi`
takes precedence over its `.py` for every importer regardless of how the module builds itself. The `.py` comes off the
ruff, codespell, and coverage exclude lists once it is hand-written; the `.pyi` stays on them. The `globals()`
assignments may need a narrow `# type: ignore` for BasedPyright; if that turns into a fight, keeping the `.py` on the
basedpyright exclude is an acceptable fallback, since the stub is what callers are checked against.

## Risks / Trade-offs

- [The floor question decides everything] If the floor stays at 5.29 this change buys nothing user-visible. See
  `proposal.md`.
- [Silent surface drift] A future libpg_query bump could change the schema in a way the loader publishes differently
  from gencode, with no protoc-generated `.py` to diff against. Mitigated by a test that walks `DESCRIPTOR` and asserts
  a module attribute exists for every message, enum, and enum value — plus behavioural assertions, per the pickle defect
  above.
- [Import-time cost] +10 ms on upb, +90 ms on the pure-Python backend. Measured above.
- \[Loss of `linguist-generated`\] `pg_query_pb2.py` starts appearing in diffs and language statistics. That is correct
  — it becomes real source.
