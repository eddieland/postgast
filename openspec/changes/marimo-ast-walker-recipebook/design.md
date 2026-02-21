## Context

postgast provides `walk()` and `Visitor` for AST traversal but has no interactive examples showing how to apply them.
The library's public API (`parse`, `deparse`, `walk`, `Visitor`, `pg_query_pb2`) is stable and well-tested. Marimo is a
reactive Python notebook framework that stores notebooks as pure `.py` files — clean diffs, no JSON, runnable as
scripts.

## Goals / Non-Goals

**Goals:**

- Provide executable recipes for the most common AST walker use cases
- Each recipe is self-contained: SQL input, analysis code, formatted output — all in one cell
- Runnable both interactively (`marimo edit`) and as a read-only app (`marimo run`)
- Demonstrate both `walk()` and `Visitor` approaches so users can compare

**Non-Goals:**

- Not a comprehensive API reference or tutorial — recipes assume basic postgast familiarity
- Not a test suite — recipes demonstrate patterns, not exhaustive edge cases
- Not covering `normalize`, `fingerprint`, `split`, or `scan` — focused on tree walking only
- Not building reusable helper functions — each recipe is intentionally standalone

## Decisions

### 1. Marimo over Jupyter

**Choice**: Marimo notebook (`.py` file)

**Alternatives considered**:

- **Jupyter (`.ipynb`)**: JSON format produces noisy diffs; requires jupyter in dev deps; cell output stored in file
  bloats the repo
- **Plain Python scripts**: No interactivity; can't tweak SQL and see results update
- **Sphinx/docs examples**: Static; can't run or modify

**Rationale**: Marimo stores notebooks as plain Python with `@app.cell` decorators — git-friendly, reactive, and
executable as a standalone script. Users can `marimo edit` to experiment or `marimo run` to view as an app.

### 2. Single notebook with sectioned cells

**Choice**: One file `recipes/ast_walker.py` with a header cell, recipe cells grouped by theme, and a shared imports
cell.

**Alternatives considered**:

- **Multiple notebooks** (one per recipe): More files to manage, harder to discover, duplicated imports
- **One cell per recipe**: Too granular — related setup and output split awkwardly

**Rationale**: A single notebook keeps everything discoverable. Marimo's reactive model means cells can share the
`postgast` import without coupling. Each recipe cell is self-contained (defines its own SQL, runs its own analysis,
renders its own output).

### 3. Cell structure convention

Each recipe cell follows a consistent pattern:

```python
@app.cell
def _(mo, parse, walk):  # declare dependencies
    sql = "SELECT ..."
    tree = parse(sql)
    # ... analysis using walk() or Visitor ...
    mo.md(f"## Recipe Title\n\n{result}")
    return ()  # no exports unless needed by another cell
```

**Rationale**: Declaring postgast imports as cell parameters makes dependencies explicit and lets marimo manage reactive
updates. Returning empty tuple signals the cell is a leaf — no downstream dependents.

### 4. Dependency management

**Choice**: Add `marimo` to the `[project.optional-dependencies]` table under a `recipes` extra.

```toml
[project.optional-dependencies]
recipes = ["marimo>=0.10"]
```

**Alternatives considered**:

- **Dev dependency group**: Recipes aren't dev tooling — they're user-facing examples
- **No dependency**: Users would need to know to `pip install marimo` separately

**Rationale**: An optional extra keeps the core package lightweight while making `uv sync --extra recipes` a one-step
setup. The `recipes` extra name makes intent clear.

### 5. Recipe selection

The notebook covers six recipes progressing from simple to complex:

1. **Extract table names** — `Visitor` with `visit_RangeVar`, the "hello world" of AST walking
1. **Collect column references** — `walk()` generator filtering for `ColumnRef` messages
1. **Classify statement type** — Pattern-match on top-level statement node type
1. **Detect subqueries** — Nested `SelectStmt` detection via `walk()` depth tracking
1. **Measure query complexity** — Count nodes, joins, conditions as a complexity heuristic
1. **Map schema dependencies** — Build a table dependency graph from DDL + DML

**Rationale**: These cover the most frequently asked "how do I..." questions for SQL parsers. They progress from
single-node-type visitors to multi-pass whole-tree analysis, demonstrating increasing sophistication.

## Risks / Trade-offs

- **[Marimo version churn]** → Pin minimum version (`>=0.10`) but no upper bound; notebook format is stable across minor
  versions. Recipes use only core `mo.md()` and `@app.cell` — no experimental APIs.
- **[Protobuf API coupling]** → Recipes reference specific node types (`RangeVar`, `ColumnRef`, `SelectStmt`) tied to
  the libpg_query protobuf schema. If the upstream schema changes, recipes may need updates. Mitigated by using only
  well-established PostgreSQL AST node types.
- **[Not automatically tested]** → Recipes aren't run in CI. A recipe could break silently if the postgast API changes.
  Acceptable for now — the unit tests cover the underlying API, and recipes are demonstrative rather than contractual.
