## Context

postgast has a complete ctypes foundation: library loading, C struct bindings, and function signatures for all
libpg_query operations. However, there is no public Python API — users cannot call any function. `normalize` is the
first public function and establishes the patterns (error handling, result lifecycle, module layout) that all subsequent
functions will reuse.

The C function `pg_query_normalize` takes a `const char*` SQL string and returns a `PgQueryNormalizeResult` containing
either a `normalized_query` string or an error pointer. The result must always be freed via
`pg_query_free_normalize_result`.

## Goals / Non-Goals

**Goals:**

- Establish a reusable error-handling pattern: C error struct to Python exception.
- Establish a reusable result lifecycle pattern: call, check error, extract value, free (always).
- Expose `normalize()` as the first public API function.
- Set up the module layout convention: private `_module.py` implementations, clean `__init__.py` re-exports.

**Non-Goals:**

- Implementing any other public API function (parse, deparse, fingerprint, split, scan).
- Protobuf deserialization (normalize does not use protobuf).
- Adding runtime dependencies.

## Decisions

### Module layout: private implementation modules with `__init__.py` re-exports

`__init__.py` stays clean as the public surface, re-exporting names from private modules. Implementation lives in
underscore-prefixed modules (`_errors.py`, `_normalize.py`).

**Why**: Keeps the public interface declarative and easy to scan. Users see `from postgast import normalize` without
navigating internal structure. Follows the existing `_native.py` convention.

**Alternative considered**: Everything in `__init__.py`. Rejected — mixes interface with implementation and will not
scale as more functions are added.

### Custom exception class `PgQueryError` inheriting from `Exception`

A structured exception with attributes: `message`, `cursorpos`, `context`, `funcname`, `filename`, `lineno`.

**Why**: The C error struct provides rich information (especially `cursorpos` for pinpointing errors in SQL). A custom
exception surfaces these fields for programmatic access. Inheriting from `Exception` (not `ValueError` or
`RuntimeError`) gives users flexibility in catch hierarchies.

**Alternative considered**: Plain `ValueError` with formatted message string. Rejected — loses structured fields,
especially `cursorpos` which is valuable for editor integrations and error reporting.

### Helper function `_check_error` to centralize C-to-Python error translation

A private function that inspects the error pointer on any result struct. If set, it extracts the fields, frees the
result, and raises `PgQueryError`. Called at the top of every public API function after the C call.

**Why**: Every public function follows the same error-check pattern. Centralizing it avoids duplication and ensures
consistent error messages across all six operations.

### Encoding: Python `str` in, `str` out — UTF-8 internally

Public functions accept `str` and return `str`. Encoding to `bytes` (UTF-8) for the C call and decoding the result back
to `str` happens inside the implementation. PostgreSQL uses UTF-8 as its default encoding.

**Why**: The natural Python interface is strings, not bytes. Users should not need to think about encoding.

### Result lifecycle: try/finally to guarantee freeing

Every C call is wrapped in try/finally to ensure the result struct is freed via the corresponding `pg_query_free_*`
function, regardless of whether an error occurred.

**Why**: The C library allocates memory for results. Failing to free causes memory leaks. try/finally is simple and
reliable.

## Risks / Trade-offs

- **Name collision with `PgQueryError` C struct**: The Python exception `PgQueryError` shares a name with the C struct
  in `_native.py`. Acceptable because the C struct is internal (`_native.PgQueryError`) and the Python exception is
  public (`postgast.PgQueryError`). No ambiguity in practice.

- **`cursorpos` is 1-indexed from C**: The raw cursor position from libpg_query is 1-based. We pass it through as-is
  rather than converting to 0-based, since PostgreSQL's own error messages use 1-based positions. Document this.
