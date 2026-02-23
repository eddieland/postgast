# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

postgast is a BSD-licensed Python library providing bindings to [libpg_query](https://github.com/pganalyze/libpg_query),
the PostgreSQL parser extracted as a standalone C library. It calls libpg_query's C functions via Python's `ctypes`
module — no Cython, Rust, or C extensions. Parse results are protobuf messages deserialized into Python objects.

Core operations: parse, deparse, normalize, fingerprint, split, and scan PostgreSQL SQL.

## Commands

```bash
make install       # Install dependencies (uv sync --all-extras)
make fmt           # Autoformat: mdformat, codespell, ruff check --fix, ruff format
make lint          # Format + type-check (basedpyright)
make test          # Run tests
make coverage      # Run tests with coverage + HTML report (htmlcov/)
make all           # install + lint + test
```

Run a single test:

```bash
uv run pytest tests/test_foo.py::test_bar -v
```

All commands use `uv run` to execute within the project virtualenv.

## Architecture

- **`src/postgast/`** — Package source (installed via `hatchling` with `packages = ["src/postgast"]`)
- **`tests/`** — Test directory (pytest discovers from both `src` and `tests` via `testpaths`)
- Uses `uv` for dependency management and `hatchling` for building
- Version is derived from git tags via `uv-dynamic-versioning`
- **`__init__.py`** is kept simple — used for clean re-exports so users get a nice public API
- Uses the official `protobuf` library (not a lighter alternative) for reliability

## Module Naming

New modules in `src/postgast/` should use plain names (e.g., `split.py`, `helpers.py`) — **not** underscore-prefixed
names. The existing `_*.py` modules are a legacy convention that will be renamed. The public API is defined by
`__init__.py` re-exports and `__all__`, not by module name prefixes.

## Code Style & Tooling

- **Formatter/Linter**: Ruff (line-length 120, Google-style docstrings)
- **Type checker**: BasedPyright (configured in `pyproject.toml`)
- **Spell checker**: codespell
- **Markdown formatter**: mdformat
- Python 3.10+ (minimum version)
- Tests use `pytest`; coverage via `pytest-cov` (`make coverage`)

## uv Best Practices

Always use `uv run` to execute commands — never activate the virtualenv manually or use bare `pip`.

**Selecting dependencies for a run:**

- `uv run <cmd>` — uses the project's locked environment (core deps + dev group)
- `uv run --extra recipes <cmd>` — include an optional extra for the run
- `uv run --with <pkg> <cmd>` — temporarily add a package for a single invocation without modifying `pyproject.toml`
  (useful for one-off tools or debugging aids)
- `uv run --only-group dev <cmd>` — run with only a specific dependency group, excluding core deps

**Adding dependencies — put them in the right place:**

- `uv add <pkg>` — core dependency (shipped to users, keep this minimal)
- `uv add --dev <pkg>` — dev-only tooling (linters, test runners, type checkers)
- `uv add --optional recipes <pkg>` — optional extra (for the `recipes` extra group)

**Other useful commands:**

- `uv tool run <pkg>` (or `uvx <pkg>`) — run a standalone CLI tool without installing it into the project
- `uv sync --all-extras` — install everything (what `make install` does)
- `uv sync --upgrade --all-extras --dev` — upgrade all deps to latest compatible versions

**Things to avoid:**

- Don't use `pip install` — it bypasses uv's lockfile and can desync the environment
- Don't create or activate venvs manually — `uv run` and `uv sync` handle this
- Don't add heavy packages to core `dependencies` if they're only needed for dev or optional features

## README Feature Matrix

The feature matrix table in `README.md` must be kept in sync with project status. Update it at these progression points:

- **After finishing apply** — set status to `Available` with a link to the spec directory (e.g.,
  `[Available](openspec/specs/feature/)`)
- **After archiving a change** — confirm the status is `Available` and the spec link is correct; add new rows if the
  change introduced a major feature not yet listed

**Only add rows for major library pillars** — top-level capabilities a user would evaluate when choosing the library
(e.g., parse, deparse, normalize, split). Do not add rows for minor helpers, internal utilities, or small convenience
functions. If a change enhances an existing feature rather than introducing a new pillar, update the existing row
instead of adding a new one.

Do not update the matrix during intermediate steps (planning, drafting specs, mid-implementation).
