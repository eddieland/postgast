## Why

postgast wraps libpg_query's C functions via ctypes, passing user-supplied SQL strings directly to native code.
Malformed, adversarial, or edge-case inputs could trigger crashes, segfaults, or memory corruption in the C layer that
currently go undetected by the existing unit tests. Fuzz testing systematically explores unexpected inputs to surface
these issues before users encounter them in production.

## What Changes

- Add property-based fuzz tests using Hypothesis that exercise all six string-accepting public functions (`parse`,
  `normalize`, `fingerprint`, `scan`, `split`, `deparse`) with generated inputs
- Fuzz the string→C boundary (arbitrary text, binary-ish strings, empty strings, oversized inputs) to verify that all
  inputs either return a valid result or raise `PgQueryError` — never segfault or leak memory
- Fuzz the protobuf→C boundary (`deparse`) with mutated parse trees to verify robustness against malformed ASTs
- Add a `make fuzz` command for running fuzz tests independently of the standard test suite

## Capabilities

### New Capabilities

- `fuzz-testing`: Property-based fuzz tests targeting the ctypes boundary between Python and libpg_query, covering all
  public functions with generated and mutated inputs

### Modified Capabilities

## Impact

- **New files**: `tests/postgast/test_fuzz.py` — fuzz test module
- **Modified files**: `pyproject.toml` — add `hypothesis` as a dev dependency; `Makefile` — add `fuzz` target
- **Dependencies**: `hypothesis` (dev-only)
- **No changes** to any `src/postgast/` source files — this is purely additive testing infrastructure
