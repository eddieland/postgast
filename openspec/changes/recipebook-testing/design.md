## Context

The three recipebooks (`ast_walker.py`, `batch_processing.py`, `sql_transforms.py`) are marimo notebooks that
demonstrate postgast API usage. They have no automated test coverage. Marimo's `App.run()` method executes all cells
synchronously in script mode (no server, no UI) and returns `(outputs, defs)`. If any cell raises, `App.run()` raises.
This makes it a natural fit for CI smoke testing.

## Goals / Non-Goals

**Goals:**

- Catch API drift — when postgast functions are renamed, removed, or change signature, recipe tests fail
- Run in CI automatically on every push
- Keep the test trivially simple — no duplicated logic, no hand-written assertions per recipe

**Non-Goals:**

- Testing marimo's rendering/UI behavior
- Asserting specific output values from recipe cells (the recipes demonstrate patterns, not produce fixed outputs)
- Achieving line-level coverage of recipe files

## Decisions

### Decision 1: Run recipes via `app.run()`, not replicate logic in tests

Import each recipe module and call its `app.run()` method. This executes every cell in topological order. If any cell
fails (import error, TypeError, AttributeError, etc.), the test fails.

**Why over replicating logic:** The previous approach would have written ~19 test methods that duplicate recipe logic
with hand-written assertions. That creates a maintenance burden and doesn't actually test the recipes — it tests
reimplementations. Running the real recipes catches the exact drift we care about (API changes, signature changes) with
zero duplication.

**Trade-off:** We don't assert specific output values. A recipe cell could silently produce wrong results without
failing. This is acceptable — the recipes are demonstrations, not production code. The important thing is that they
*run*.

### Decision 2: Parametrize over recipe modules

A single parametrized test function discovers and runs each recipe. Adding a new recipe file only requires adding it to
the parameter list.

### Decision 3: `pytest.importorskip("marimo")` for graceful skip

The test file uses `pytest.importorskip("marimo")` at module level. When marimo is not installed (e.g., a contributor
runs `make test` without `--extra recipes`), the entire test file is skipped rather than failing.

### Decision 4: Install `recipes` extra in CI

The CI test job installs with `--extra recipes` so that marimo is available and recipe tests run. This is a small
addition to the existing `uv sync` step.

## Risks / Trade-offs

- **[Marimo version sensitivity]** A marimo upgrade could change `App.run()` behavior. → Low risk; `app.run()` is
  marimo's documented programmatic API. Pin `marimo>=0.10` in the `recipes` extra.
- **[Silent wrong results]** Recipes could produce incorrect output without raising. → Acceptable; recipes are demos.
  Core API correctness is covered by the existing unit test suite.
- **[Recipe bugs block CI]** Existing recipes have bugs (e.g., passing strings to `find_nodes` instead of types) that
  must be fixed before these tests pass. → Fix as part of this change.
