## Context

postgast has a working ctypes foundation and one public function (`normalize`). The ctypes bindings for
`pg_query_parse_protobuf` and its free function are already declared in `_native.py`. The vendored `pg_query.proto`
defines the `ParseResult` message (containing `repeated RawStmt stmts`) and 200+ AST node types via a `Node` oneof.

Adding `parse()` requires two new capabilities: the function itself and the protobuf deserialization layer. This is the
first function that returns structured data rather than a plain string, so the protobuf bindings it introduces will be
reused by future operations (scan, deparse).

## Goals / Non-Goals

**Goals:**

- Expose `parse()` as the second public API function, following the patterns established by `normalize()`.
- Generate Python protobuf bindings from the vendored `pg_query.proto` and ship them in the package.
- Return fully deserialized protobuf `ParseResult` objects so users can traverse the AST with attribute access.
- Add `protobuf` as the first (and only) runtime dependency.

**Non-Goals:**

- Providing a higher-level AST abstraction or visitor pattern on top of protobuf messages.
- Exposing the JSON-based `pg_query_parse` — protobuf is the canonical format.
- Implementing deparse, fingerprint, split, or scan (those build on this foundation but are separate changes).
- Type stubs or a `.pyi` file for the generated `_pg_query_pb2.py` — protobuf's own runtime typing is sufficient for
  now.

## Decisions

### Use `pg_query_parse_protobuf` (not `pg_query_parse`)

Call the protobuf variant of the C parse function, which returns binary protobuf bytes in a `PgQueryProtobuf` struct
(`len` + `data`), rather than the JSON variant.

**Why**: Protobuf is the canonical wire format in libpg_query. It avoids a JSON string→Python dict intermediate step.
The binary is deserialized directly into typed Python objects. Future operations (deparse) require protobuf input, so
consistency matters.

**Alternative considered**: `pg_query_parse` (JSON output) parsed with `json.loads()`. Rejected — would return untyped
dicts, lose the protobuf schema contract, and require a separate conversion step for deparse round-tripping.

### Generate `_pg_query_pb2.py` at build time, commit the result

Run `protoc --python_out` against the vendored `pg_query.proto` to produce the Python bindings. Commit the generated
file into `src/postgast/` and add a Makefile target (`make proto`) for regeneration.

**Why**: Committing the generated file means users installing from source or sdist do not need `protoc` installed. A
Makefile target makes regeneration reproducible when the vendored proto is updated. The underscore prefix
(`_pg_query_pb2.py`) signals it's internal.

**Alternative considered**: Generate at install time via a hatch build hook. Rejected — adds complexity to the build
pipeline and requires `grpcio-tools` as a build dependency, which is heavy.

### Extract protobuf bytes via `ctypes.string_at(data, len)`

The `PgQueryProtobuf` struct has `len` (size_t) and `data` (char\*). Use
`ctypes.string_at(result.parse_tree.data, result.parse_tree.len)` to copy the binary data into a Python `bytes` object
before freeing the C result.

**Why**: `c_char_p` fields auto-convert to `bytes` but are null-terminated, which truncates binary protobuf data
containing `\x00` bytes. `string_at` uses the explicit length and is safe for arbitrary binary data.

**Alternative considered**: Using `c_char_p` directly. Rejected — protobuf payloads routinely contain null bytes, which
would silently truncate the data.

### Return the protobuf `ParseResult` message directly

`parse()` returns the deserialized `pg_query.ParseResult` protobuf message object. Users access `result.version` and
`result.stmts` (a list of `RawStmt`), and can traverse the full AST via nested protobuf attributes.

**Why**: Protobuf messages are self-describing, typed, and already have a well-documented structure matching the
PostgreSQL source. No wrapper layer needed. Users familiar with libpg_query in other languages (Ruby, Go) will recognize
the same structure.

**Alternative considered**: Wrapping in dataclasses or NamedTuples. Rejected — duplicates the proto schema, adds a
maintenance burden when the proto updates, and doesn't add meaningful value over the protobuf API.

### Add `protobuf` as a runtime dependency

Add `protobuf>=5.29` to `pyproject.toml` `dependencies`. This is the minimum version supporting Python 3.10+ with the
current proto3 syntax.

**Why**: The official `protobuf` library is required for deserializing the binary parse output. It's well-maintained by
Google, widely used, and the AGENTS.md explicitly specifies using "the official protobuf library (not a lighter
alternative) for reliability."

**Alternative considered**: `betterproto` or manual binary parsing. Rejected — AGENTS.md explicitly calls for the
official library; manual parsing is fragile across proto schema updates.

### Follow the `normalize()` module pattern exactly

Create `_parse.py` with the same structure: import `check_error` and `lib` from internal modules, encode input to UTF-8,
call the C function, check error, extract result, free in `finally`.

**Why**: Consistency. Every public function should look the same. The pattern is proven to be memory-safe and ergonomic.

## Risks / Trade-offs

- **First runtime dependency**: Adding `protobuf` breaks the zero-dependency property. This is intentional — protobuf
  deserialization is core to the library's purpose and was always planned. The `protobuf` package is pure Python with
  optional C acceleration, so it won't cause platform compatibility issues.

- **Generated code maintenance**: `_pg_query_pb2.py` must be regenerated when the vendored `pg_query.proto` is updated
  (i.e., when bumping the libpg_query version). The `make proto` target and a note in AGENTS.md mitigate this. →
  Mitigation: CI can verify the generated file is up-to-date.

- **Protobuf message API is verbose for deep traversal**: Accessing a column name in a SELECT requires navigating
  several nested levels (e.g., `result.stmts[0].stmt.select_stmt.target_list[0].res_target.val.column_ref...`). This is
  inherent to the PostgreSQL AST structure, not something we should abstract away in this change. → Mitigation:
  Documentation with examples.

- **`string_at` copies the buffer**: The `ctypes.string_at` call copies protobuf bytes from C memory into a Python bytes
  object. For very large SQL strings this is an extra allocation, but it's necessary because we free the C result
  immediately after. The copy is negligible for any realistic query size.
