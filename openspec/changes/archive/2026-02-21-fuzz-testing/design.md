## Context

postgast exposes six public functions that pass user input across a ctypes boundary into libpg_query's C code. Five
accept arbitrary SQL strings (`parse`, `normalize`, `fingerprint`, `scan`, `split`) and one accepts a protobuf parse
tree (`deparse`). The existing test suite covers expected inputs and known error cases but does not systematically
explore edge cases or adversarial inputs. A crash at the C layer surfaces as a Python segfault with no traceback — hard
to diagnose and impossible to catch.

## Goals / Non-Goals

**Goals:**

- Verify that every public function either returns a valid result or raises `PgQueryError` for any input — never
  crashes, hangs, or corrupts memory
- Cover both the string→C boundary (all five string-accepting functions) and the protobuf→C boundary (`deparse`)
- Run quickly enough to be useful in development (`make fuzz` target) without being part of the default test suite
- Use property-based testing to explore inputs that hand-written tests would miss

**Non-Goals:**

- Coverage-guided fuzzing (e.g., Atheris/libFuzzer) — requires C instrumentation and a more complex build; can be added
  later
- Fuzzing libpg_query internals directly — we test at the Python API boundary
- Performance benchmarking — this is about correctness and crash-freedom, not speed
- Fuzz testing the protobuf deserialization layer itself (handled by the `protobuf` library)

## Decisions

### Use Hypothesis for property-based testing

**Choice**: Hypothesis over Atheris or raw random generation.

**Rationale**: Hypothesis integrates natively with pytest, supports example databases for regression, has mature
text/binary strategies, and requires no C-level instrumentation. It's the standard for Python property-based testing.
Atheris would provide coverage-guided fuzzing of the C code itself but requires compiling libpg_query with sanitizer
instrumentation — a significant build complexity increase for a later iteration.

**Alternatives considered**:

- Atheris (Google's Python fuzzer) — better C coverage but requires instrumented builds
- Raw `random` + loops — no shrinking, no example database, no reproducibility

### Strategy design: text-based with SQL-flavored bias

**Choice**: Layer Hypothesis strategies to generate a mix of arbitrary text, SQL-like fragments, and edge-case strings.

**Rationale**: Pure random bytes rarely exercise interesting parser paths. Mixing in SQL keywords, operators, and
structure (parentheses, semicolons, quotes) increases the chance of hitting interesting parser states while Hypothesis's
random text covers the unexpected-input space.

Strategies (composited via `st.one_of`):

- `st.text()` — arbitrary Unicode text
- `st.binary().map(decode)` — binary data decoded with error replacement
- SQL fragment generator — combines keywords, identifiers, operators, literals, and punctuation
- Edge cases — empty string, null bytes, very long strings, deeply nested parens

### Separate pytest mark and Makefile target

**Choice**: Mark fuzz tests with `@pytest.mark.fuzz` and add a `make fuzz` target.

**Rationale**: Fuzz tests are inherently slower (Hypothesis runs many examples per test) and non-deterministic in
timing. Keeping them out of the default `make test` run prevents CI slowdowns while making them easy to run on demand.
The mark also allows `pytest -m fuzz` for selective execution.

### Single test file

**Choice**: All fuzz tests in `tests/postgast/test_fuzz.py`.

**Rationale**: There's one capability being fuzzed (the ctypes boundary) across multiple functions. A single file keeps
the fuzz strategy definitions co-located and avoids scattering related tests. Each function gets its own test method
within a `TestFuzz` class.

### The crash-freedom property

**Choice**: Each fuzz test asserts that the function either returns normally or raises `PgQueryError`. Any other
exception (especially `SystemError`, segfault, or hang) is a failure.

**Rationale**: This is the core safety property. We don't validate the correctness of parse results for random input —
just that the library never crashes. For `deparse`, we additionally fuzz with parse→mutate→deparse to test malformed
ASTs.

## Risks / Trade-offs

- **False sense of security** → Hypothesis explores inputs heuristically, not exhaustively. Mitigated by using
  `@settings(max_examples=1000)` for meaningful coverage and documenting that this complements (not replaces)
  coverage-guided fuzzing.
- **Flaky CI if included in default test run** → Mitigated by using a separate `fuzz` mark and Makefile target, keeping
  fuzz tests out of the default suite.
- **Slow test runs with high example counts** → Mitigated by using a reasonable default (1000 examples) with
  `HYPOTHESIS_MAX_EXAMPLES` env var override for deeper local runs.
- **Hypothesis database growth** → Hypothesis saves failing examples to `.hypothesis/` for regression. This directory
  should be gitignored. Mitigated by adding to `.gitignore` if not already present.
