## Context

postgast exposes `parse(query: str) -> ParseResult` and `normalize(query: str) -> str` as public API functions. Both
follow the same internal pattern: encode input, call a `lib.pg_query_*` C function, check for errors, extract the
result, and free the C struct in a `finally` block. The C bindings for `pg_query_deparse_protobuf` and
`pg_query_free_deparse_result` are already declared in `_native.py` with the correct struct types.

The deparse function is the inverse of parse — it takes a `ParseResult` protobuf, serializes it to bytes, wraps those
bytes in a `PgQueryProtobuf` C struct, and passes it to `pg_query_deparse_protobuf`, which returns a
`PgQueryDeparseResult` containing the SQL string.

## Goals / Non-Goals

**Goals:**

- Provide a `deparse` function that converts a `ParseResult` protobuf back into a SQL string
- Follow the exact same module/error/free pattern as `_parse.py` and `_normalize.py`
- Support the parse → modify → deparse round-trip workflow

**Non-Goals:**

- Pretty-printing or SQL formatting (libpg_query's deparser produces minimal, canonical SQL)
- Accepting individual statement nodes — the C API requires a full `ParseResult` protobuf
- Deparse from JSON parse trees (only protobuf is supported by the C function)

## Decisions

### 1. Input type: `ParseResult` protobuf message

**Decision**: Accept `ParseResult` (the same type returned by `parse()`) as the input.

**Rationale**: `pg_query_deparse_protobuf` expects a serialized `ParseResult` protobuf. Using the same type that
`parse()` returns makes the round-trip natural: `deparse(parse(sql))`. Accepting lower-level types (raw bytes,
individual nodes) would add API surface without clear benefit since users can always wrap nodes in a `ParseResult`.

### 2. Construct `PgQueryProtobuf` struct from serialized bytes

**Decision**: Serialize the protobuf message with `SerializeToString()`, then construct a `PgQueryProtobuf` C struct
with `len` and `data` fields pointing to the serialized bytes.

**Rationale**: The C function takes a `PgQueryProtobuf` struct (not a pointer), matching the signature already declared
in `_native.py`. We must keep a reference to the serialized bytes alive for the duration of the C call to prevent
garbage collection.

### 3. Module structure: `_deparse.py`

**Decision**: Create `src/postgast/_deparse.py` following the single-function-per-module pattern established by
`_parse.py` and `_normalize.py`.

**Rationale**: Consistency with existing code. The underscore prefix marks it as internal; the public API is exported
from `__init__.py`.

### 4. Return type: `str`

**Decision**: Return a plain `str` containing the deparsed SQL.

**Rationale**: The C function returns a `query` field (`c_char_p`) containing the SQL text. A string is the natural
Python representation and mirrors how `normalize()` returns its result.

## Risks / Trade-offs

- **Canonical SQL differs from original** → Expected behavior. libpg_query's deparser produces valid but canonicalized
  SQL (e.g., `SELECT 1` may become `SELECT 1`; identifier casing and whitespace may differ). This is a libpg_query
  characteristic, not something we control. Document this in the docstring.
- **Invalid protobuf input** → The C function will return an error via `PgQueryDeparseResult.error`, which `check_error`
  will convert to `PgQueryError`. No additional validation needed on the Python side.
