## Why

postgast currently only exposes `normalize()`. Parsing SQL into a structured AST is the core use case for libpg_query
bindings — it's the reason most users would install this library. The ctypes bindings for `pg_query_parse_protobuf` are
already declared in `_native.py`; we just need the public function and protobuf deserialization layer.

## What Changes

- Add a `parse()` function that takes a SQL string and returns a deserialized protobuf `ParseResult` object containing
  the AST
- Call `pg_query_parse_protobuf` (binary protobuf output) rather than `pg_query_parse` (JSON output) — protobuf is the
  canonical wire format and avoids a JSON→Python conversion step
- Generate Python protobuf bindings (`pg_query_pb2.py`) from the vendored `pg_query.proto` file
- Add `protobuf` as a runtime dependency in `pyproject.toml`
- Re-export `parse` and the generated protobuf module from `__init__.py` so users get `from postgast import parse` and
  can inspect AST node types

## Capabilities

### New Capabilities

- `parse`: The `parse()` public API function — accepts a SQL string, calls `pg_query_parse_protobuf` via ctypes,
  deserializes the binary result using the generated protobuf bindings, and returns a `ParseResult` message object
- `protobuf-bindings`: Generated Python protobuf module (`pg_query_pb2.py`) providing typed AST node classes
  (`ParseResult`, `RawStmt`, `SelectStmt`, `Node`, etc.) from the vendored `pg_query.proto`

### Modified Capabilities

_(none — no existing spec requirements change)_

## Impact

- **New files**: `src/postgast/_parse.py`, `src/postgast/_pg_query_pb2.py` (generated), build-time proto generation
  script or Makefile target
- **Modified files**: `src/postgast/__init__.py` (add `parse` + protobuf re-exports), `pyproject.toml` (add `protobuf`
  runtime dependency)
- **Dependencies**: Adds `protobuf` as the first runtime dependency (required for deserialization)
- **C API surface**: Uses `pg_query_parse_protobuf` and `pg_query_free_protobuf_parse_result` (both already declared in
  `_native.py`)
- **Tests**: New unit tests for `parse()` covering basic SELECT/INSERT/UPDATE/DELETE, multi-statement input, syntax
  error handling, and AST node type assertions
