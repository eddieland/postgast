## Context

postgast wraps libpg_query's C functions via ctypes. Every public operation — parse, deparse, normalize, fingerprint,
split, scan — crosses the Python/C boundary: Python strings are encoded to `bytes`, passed to C, and results come back
as C structs (freed with `pg_query_free_*`). The existing ~145 tests cover normal SQL patterns thoroughly but never push
scale limits or exercise pathological inputs. Since bugs at the ctypes boundary can manifest as segfaults or memory
corruption rather than clean Python exceptions, this gap is worth closing.

## Goals / Non-Goals

**Goals:**

- Confirm every public function handles pathological inputs without crashing (segfault, abort, hang)
- Document empirical scale limits of libpg_query as exercised through postgast
- Verify that `PgQueryError` is raised cleanly for all classes of malformed input
- Verify no state leakage between sequential calls (error or success)
- Keep stress tests isolated so they can be skipped in fast CI loops

**Non-Goals:**

- Performance benchmarking or optimization — we're testing correctness, not speed
- Exhaustive SQL grammar coverage — that's the job of the existing roundtrip/functional tests
- Testing libpg_query internals — we only test what's reachable through postgast's public API
- Modifying library source code or changing error handling behavior

## Decisions

### 1. Two test files, not one

**Decision**: `test_stress.py` for scale/resource tests, `test_boundary.py` for edge-case inputs.

**Rationale**: Stress tests are slow (large inputs, deep nesting) and may need to be excluded from fast CI. Boundary
tests are fast (small pathological inputs) and should always run. Separating them allows `pytest -m "not stress"` to
skip only the slow tests.

**Alternative considered**: A single `test_stress_boundary.py` file. Rejected because it conflates fast and slow tests,
making selective execution harder.

### 2. Use a `stress` pytest marker

**Decision**: Register a `stress` marker in `pyproject.toml` and apply it to all tests in `test_stress.py`. Boundary
tests get no special marker — they're fast and should always run.

**Rationale**: Lets CI configurations and developers skip slow tests with `-m "not stress"` without skipping the
important boundary-condition coverage.

**Alternative considered**: Using `@pytest.mark.slow`. Rejected because "stress" is more descriptive of the intent —
these aren't just slow, they deliberately push limits.

### 3. Test all six core operations uniformly

**Decision**: Both test files cover all six public functions (`parse`, `deparse`, `normalize`, `fingerprint`, `split`,
`scan`) with the same categories of inputs where applicable.

**Rationale**: Each operation has its own C function and ctypes binding. A crash in `pg_query_normalize` wouldn't
necessarily reproduce in `pg_query_parse`. Uniform coverage avoids blind spots.

**Alternative considered**: Testing only `parse` and `split` since they're the most complex. Rejected because the cost
of including all six is minimal and the safety benefit is real.

### 4. Use `pytest.mark.parametrize` for input variations

**Decision**: Group related inputs into lists and use `@pytest.mark.parametrize` to fan them out, following the pattern
established in `test_roundtrip.py`.

**Rationale**: Keeps tests DRY, produces clear per-case output in test reports, and aligns with the existing project
style.

### 5. Deparse stress tests use round-trip through parse first

**Decision**: For `deparse` stress/boundary tests, first `parse()` a known-valid large query, then `deparse()` the
resulting protobuf. We don't craft raw protobuf messages.

**Rationale**: `deparse` takes a protobuf `ParseResult`, not a string. The only realistic way to get a complex
`ParseResult` is to parse real SQL. Testing deparse with hand-crafted protobuf would be testing protobuf construction,
not deparse behavior.

### 6. Expect errors or success — never crashes

**Decision**: Every test asserts one of: (a) the function returns a result, or (b) it raises `PgQueryError`. A test that
causes a segfault or hang is itself a finding, but the test assertions only cover the clean outcomes.

**Rationale**: We can't assert "no segfault" in pytest. If a test segfaults, pytest will abort with a non-zero exit —
that's the signal. The test logic only needs to exercise the input; the assertion is a sanity check on the output shape.

## Risks / Trade-offs

**[Stress tests are slow]** → Mark with `@pytest.mark.stress` and document how to skip them. Keep individual test cases
bounded (e.g., cap nesting at ~500 levels, cap SQL size at ~10 MB) so CI doesn't time out.

**[libpg_query may intentionally reject large inputs]** → That's fine — a `PgQueryError` is a valid outcome. The test
passes as long as there's no crash. We'll document discovered limits in test comments.

**[Null bytes may behave differently across platforms]** → C strings are null-terminated, so embedded `\x00` in Python
strings will truncate at the ctypes boundary. Tests should verify the library doesn't crash; the exact behavior
(truncation vs error) is libpg_query's choice.

**[Test maintenance burden]** → Minimal. These tests exercise the public API with static inputs. They don't depend on
implementation details and shouldn't break unless the library's error handling changes.
