## Context

The C bindings for `pg_query_scan` and `pg_query_free_scan_result` are already declared in `_native.py`, and the
protobuf types (`ScanResult`, `ScanToken`, `Token`, `KeywordKind`) are generated in `_pg_query_pb2.py`. Every other
protobuf-returning function (`parse`, `deparse`) follows the same call → check → extract → deserialize → free pattern.
Scan is the same shape — no new patterns needed.

## Goals / Non-Goals

**Goals:**

- Expose `pg_query_scan` as `postgast.scan(sql) -> ScanResult`
- Follow the established function pattern (encode → call → check_error → extract protobuf → deserialize → free)
- Full unit test coverage for the public function

**Non-Goals:**

- Higher-level token iteration helpers or pretty-printing — users work with the protobuf `ScanResult` directly
- Custom Python token classes wrapping the protobuf types
- Streaming or incremental tokenization

## Decisions

### 1. Return `ScanResult` protobuf directly

Return the deserialized `ScanResult` message as-is, consistent with `parse()` returning `ParseResult`.

**Alternative considered**: Wrap tokens in custom Python dataclasses for a more Pythonic API. Rejected because every
other function returns protobuf types directly, and adding a wrapper would break consistency and add maintenance burden
for no clear benefit.

### 2. Single module `_scan.py`

Place the implementation in `src/postgast/_scan.py` following the naming convention of `_parse.py`, `_normalize.py`,
etc.

### 3. Protobuf extraction via `ctypes.string_at`

Use `ctypes.string_at(pbuf.data, pbuf.len)` to extract binary protobuf data, same as `_parse.py`. This safely handles
embedded null bytes that `c_char_p` would truncate.

## Risks / Trade-offs

- **[Minimal implementation risk]** → The C bindings, protobuf types, and function pattern all exist. This is a
  mechanical addition.
- **[Byte positions, not character positions]** → `ScanToken.start` and `ScanToken.end` are byte offsets, not character
  offsets. For multi-byte UTF-8 input, users must convert if they need character positions. This matches libpg_query's
  behavior and is documented, not mitigated.
