# CLAUDE.md

## Project Overview

postgast — BSD-licensed Python bindings to [libpg_query](https://github.com/pganalyze/libpg_query) via `ctypes` (no Cython/Rust/C extensions). Parse results are protobuf messages deserialized into Python objects. Core ops: parse, deparse, normalize, fingerprint, split, scan.

## Commands

```bash
make install       # uv sync --all-extras
make fmt           # mdformat, codespell, ruff check --fix, ruff format
make lint          # fmt + basedpyright
make test          # pytest
make coverage      # pytest-cov + HTML report (htmlcov/)
make all           # install + lint + test
uv run pytest tests/test_foo.py::test_bar -v  # single test
```

## Architecture

- `src/postgast/` — package source (hatchling, `packages = ["src/postgast"]`)
- `tests/` — pytest test directory
- `uv` for deps, `hatchling` for build, version from git tags (`uv-dynamic-versioning`)
- `__init__.py` — clean re-exports defining the public API
- Uses official `protobuf` library

## Conventions

- New modules: plain names (`split.py`), not underscore-prefixed. Existing `_*.py` is legacy.
- Public API defined by `__init__.py` re-exports and `__all__`, not module prefixes.
- Ruff: line-length 120, Google-style docstrings. Type checker: BasedPyright. Python 3.10+.
- Always use `uv run` — never bare `pip install` or manual venv activation.
- `uv add <pkg>` = core dep (keep minimal), `uv add --dev <pkg>` = dev-only, `uv add --optional recipes <pkg>` = optional extra.

## README Feature Matrix

Keep the feature matrix in `README.md` in sync. Update after finishing apply or archiving a change — set status to `Available` with spec link (e.g., `[Available](openspec/specs/feature/)`). Only add rows for major library pillars (parse, deparse, normalize, split, etc.), not minor helpers. Don't update during intermediate steps.
