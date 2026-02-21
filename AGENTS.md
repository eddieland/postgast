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
make test          # Run all tests (unit + integration, requires Docker)
make test-unit     # Run unit tests only (no Docker)
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

## Code Style & Tooling

- **Formatter/Linter**: Ruff (line-length 120, Google-style docstrings)
- **Type checker**: BasedPyright (configured in `pyproject.toml`)
- **Spell checker**: codespell
- **Markdown formatter**: mdformat
- Python 3.10+ (minimum version)
- Tests use `pytest`; integration tests are marked with `@pytest.mark.integration` and require Docker

## README Feature Matrix

The feature matrix table in `README.md` must be kept in sync with project status. Update it at these progression points:

- **After finishing apply** — set status to `Available` with a link to the spec directory (e.g.,
  `[Available](openspec/specs/feature/)`)
- **After archiving a change** — confirm the status is `Available` and the spec link is correct; add new rows if the
  change introduced a feature not yet listed

Do not update the matrix during intermediate steps (planning, drafting specs, mid-implementation).
