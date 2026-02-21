## Context

The ctypes layer already declares `PgQueryFingerprintResult` (with fields `fingerprint: c_uint64` and
`fingerprint_str: c_char_p`) and the function signatures for `pg_query_fingerprint` /
`pg_query_free_fingerprint_result`. The remaining work is a thin Python wrapper following the same pattern as
`normalize()` and `parse()`.

## Goals / Non-Goals

**Goals:**

- Expose `fingerprint()` as a public function with the same call-and-free pattern used by `normalize()` and `parse()`
- Return both the numeric hash and its hex string representation
- Maintain full type-safety for BasedPyright

**Non-Goals:**

- Modifying `_native.py` — bindings already exist
- Batch fingerprinting or caching
- Fingerprint comparison utilities

## Decisions

### 1. Return type: `FingerprintResult` named tuple

Return a `typing.NamedTuple` with two fields: `fingerprint: int` and `hex: str`.

- **Why named tuple over plain int**: The C API returns two useful representations. Returning only one discards
  information. A named tuple is zero-overhead, immutable, and unpacks naturally (`fp, hex = fingerprint(query)`).
- **Why named tuple over dataclass**: Named tuples are lighter, immutable by default, and consistent with how
  `collections.namedtuple` is used in stdlib for simple value objects. No mutability or methods needed.
- **Why `hex` not `fingerprint_str`**: Shorter, clearer, and avoids confusion with Python's `str()`. Matches the
  convention of `int.hex()` / hex literal terminology.
- **Alternative considered — returning just `str`**: Simpler API, but discards the uint64 which is useful for storage
  and comparison in databases.

### 2. Module structure: `_fingerprint.py`

Single private module exporting `fingerprint()` and `FingerprintResult`, following the `_normalize.py` / `_parse.py`
pattern.

### 3. Error handling: reuse `check_error()`

Same pattern as all other functions — call `check_error(result)` before accessing fields, free in `finally`.

## Risks / Trade-offs

- **uint64 overflow in Python** → Not a risk. Python `int` has arbitrary precision; `c_uint64.value` returns a Python
  `int`.
- **Named tuple adds a type to the public API** → Acceptable trade-off for returning both values cleanly. It's a single
  flat type, not a complex object graph.
