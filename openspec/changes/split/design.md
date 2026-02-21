## Context

postgast already has ctypes bindings for `pg_query_split_with_scanner` and `pg_query_free_split_result` declared in
`_native.py`, along with a `PgQuerySplitResult` struct. However, the `stmts` field is incorrectly typed as
`POINTER(POINTER(c_int))`. The actual C struct uses `PgQuerySplitStmt **`, where `PgQuerySplitStmt` contains two int
fields (`stmt_location` and `stmt_len`) representing byte offsets into the input string.

No public `split()` function exists yet. All other operations (`parse`, `deparse`, `normalize`) follow the same pattern:
a single-function module in `src/postgast/_<name>.py` that calls the C function, checks for errors, extracts the result,
and frees the C struct in a `finally` block.

## Goals / Non-Goals

**Goals:**

- Expose a public `split(sql: str) -> list[str]` that splits multi-statement SQL into individual statements
- Fix the `PgQuerySplitResult` struct to match the actual C layout
- Follow existing module conventions (`_split.py`, re-export from `__init__.py`)

**Non-Goals:**

- Returning statement offsets or metadata — just the statement strings
- Stripping whitespace or comments from returned statements (return them as-is from the byte range)
- Adding a streaming/iterator API — a list is sufficient

## Decisions

### 1. Slice the encoded byte string, not the Python str

The C API returns byte offsets (`stmt_location`, `stmt_len`) into the UTF-8 input. We must slice the `bytes` object
produced by `str.encode("utf-8")` and then decode each slice back to `str`. Slicing the Python `str` directly would give
wrong results for inputs containing multi-byte characters.

**Alternative**: Convert byte offsets to character offsets. Rejected — adds complexity with no benefit since
encode/decode is straightforward and correct.

### 2. Add `PgQuerySplitStmt` as a ctypes Structure

Define a new `PgQuerySplitStmt(Structure)` with fields `stmt_location` and `stmt_len`, and change
`PgQuerySplitResult.stmts` from `POINTER(POINTER(c_int))` to `POINTER(POINTER(PgQuerySplitStmt))`. This correctly
mirrors the C header (`pg_query.h`).

**Alternative**: Keep `POINTER(POINTER(c_int))` and access fields by pointer arithmetic. Rejected — fragile and
unreadable.

### 3. Follow the `_normalize.py` pattern

`split()` is most similar to `normalize()` — it takes a `str`, calls a C function, extracts string data from the result,
and returns a Python value. The implementation will follow the same structure: encode input, call C function, check
error, extract result, free in `finally`.

## Risks / Trade-offs

- **[Struct layout mismatch]** → Validated against the vendored `pg_query.h` header. The `PgQuerySplitStmt` struct
  contains two consecutive `c_int` fields matching the C definition exactly.
- **[Empty input]** → `pg_query_split_with_scanner` returns `n_stmts = 0` for empty or whitespace-only input; we return
  an empty list. No special handling needed.
