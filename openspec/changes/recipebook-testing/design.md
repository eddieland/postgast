## Context

The three recipebooks (`ast_walker.py`, `batch_processing.py`, `sql_transforms.py`) are marimo notebooks that
demonstrate postgast API usage patterns. They have no automated test coverage. The existing test suite lives in
`tests/postgast/` with shared fixtures in `conftest.py`. marimo is an optional dependency under the `recipes` extra but
is not in the dev dependency group.

## Goals / Non-Goals

**Goals:**

- Validate that every recipe's core logic (parse, walk, visit, extract, normalize, fingerprint, split, scan, deparse,
  rewrite) produces correct results
- Catch regressions when postgast APIs change
- Run in CI without requiring marimo or a browser

**Non-Goals:**

- Testing marimo's rendering/UI behavior
- Testing marimo cell reactivity or dependency injection
- Modifying the recipe notebooks themselves
- Achieving line-level coverage of recipe files (they're marimo apps, not library code)

## Decisions

### Decision 1: Test recipe logic directly, not via marimo runtime

Test the postgast API patterns each recipe demonstrates as standalone pytest functions. Do not import or execute marimo
apps programmatically.

**Why over marimo cell execution:** Marimo's `App.run()` starts a server and reactive runtime — it's designed for
interactive use, not headless testing. Importing recipe modules requires marimo installed, and executing cells requires
marimo's dependency injection to wire parameters. Testing the logic directly is simpler, faster, more reliable, and
doesn't require marimo in the test environment.

**Trade-off:** We won't detect if a recipe's marimo-specific code (cell decorators, `mo.md()` formatting) breaks. This
is acceptable because marimo formatting is cosmetic and marimo itself is well-tested upstream.

### Decision 2: One test file — `tests/postgast/test_recipes.py`

All recipe tests go in a single file organized by test classes matching the recipebooks:

- `TestAstWalkerRecipes` — table extraction, column collection, statement classification, subquery detection, complexity
  measurement, dependency mapping, helpers usage, per-statement analysis
- `TestBatchProcessingRecipes` — split+parse migration, tokenization, query dedup, dependency graph, comment extraction,
  batch execution plan
- `TestSqlTransformsRecipes` — roundtrip normalization, normalize for logs, fingerprint equivalence, AST rewriting,
  ensure_or_replace, error inspection

**Why one file:** The recipes are a single feature area. One file keeps the test surface discoverable and avoids
scattering recipe tests across multiple modules.

### Decision 3: No new conftest fixtures for recipes

Recipe tests will call postgast APIs inline with their own SQL strings, matching how the recipes themselves work (each
cell defines its own SQL). The existing conftest fixtures (`select1_tree`, `users_tree`, etc.) are for the core library
tests and use different SQL strings.

**Why:** Recipe tests validate specific API usage patterns with specific SQL. Sharing fixtures would obscure what each
test actually validates and couple recipe tests to unrelated fixture definitions.

### Decision 4: No marimo dependency in dev group

marimo stays in the `recipes` optional extra only. Tests do not import marimo or recipe modules.

**Why:** Keeping marimo out of dev dependencies avoids bloating the dev environment (marimo pulls in many transitive
deps). Since we test the logic patterns rather than the notebooks, marimo is not needed.

## Risks / Trade-offs

- **[Recipe drift]** Recipe code and tests could diverge over time if recipes add new patterns not covered by tests. →
  Mitigate by organizing tests to mirror recipe structure so gaps are visible.
- **[Duplicate logic]** Tests reimplement recipe logic rather than importing it. → Acceptable because the tests are
  validating postgast API behavior, not recipe code reuse. The duplication is intentional — tests should be independent.
- **[No import smoke test]** We don't verify that recipe modules import successfully. → Low risk since recipes are
  validated by `marimo run` during development and recipe files are not imported by the library.
