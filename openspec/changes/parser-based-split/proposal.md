## Why

The current `split()` function uses `pg_query_split_with_scanner`, a fast scanner-based splitter. libpg_query also
provides `pg_query_split_with_parser`, which the upstream header explicitly recommends "for improved accuracy due the
parser adding additional token handling." Exposing the parser-based splitter gives users a more accurate option for
valid SQL while preserving the scanner-based fallback for inputs that may contain parse errors.

## What Changes

- Add `pg_query_split_with_parser` ctypes binding to the native module
- Add a `method` parameter to `split()` that selects between `"scanner"` (current default) and `"parser"`
- Default remains `"scanner"` to preserve backward compatibility — no **BREAKING** changes

## Capabilities

### New Capabilities

_(none — this extends an existing capability)_

### Modified Capabilities

- `split`: Add a `method` parameter accepting `"scanner"` (default) or `"parser"` to select the underlying libpg_query
  split function (`pg_query_split_with_scanner` vs `pg_query_split_with_parser`)

## Impact

- `src/postgast/_native.py` — new ctypes declaration for `pg_query_split_with_parser`
- `src/postgast/_split.py` — add `method` parameter, dispatch to the selected C function
- `tests/postgast/test_split.py` — new test cases for parser-based splitting
- `openspec/specs/split/spec.md` — updated requirements for the `method` parameter
