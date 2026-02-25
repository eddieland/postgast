# CLAUDE.md

## Project Overview

postgast is a BSD-licensed Python library that parses, deparses, normalizes, fingerprints, splits, and scans PostgreSQL
SQL. It binds to [libpg_query](https://github.com/pganalyze/libpg_query) via `ctypes` (no Cython/Rust/C extensions) and
deserializes results into protobuf Python objects.

## Commands

All `make` targets use `uv run` to execute within the project virtualenv.

```bash
make install       # uv sync --all-groups
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

- New modules: plain names (`split.py`), not underscore-prefixed. Existing `_*.py` modules are legacy.
- Public API defined by `__init__.py` re-exports and `__all__`, not module prefixes.
- Annotate module-level and class-level constants with `typing.Final` (e.g., `TIMEOUT: Final = 30`). No automated rule
  enforces this yet ([ruff#10137](https://github.com/astral-sh/ruff/issues/10137)), so treat it as a manual convention.
- Ruff: line-length 120, Google-style docstrings. Type checker: BasedPyright. Python 3.10+.
- Always use `uv run` — never bare `pip install` or manual venv activation.
- `uv add <pkg>` = core dep (keep minimal), `uv add --dev <pkg>` = dev-only, `uv add --group recipes <pkg>` = recipes
  group, `uv add --group docs <pkg>` = docs group.
- `uv run --with <pkg> <cmd>` — temporarily add a package for a single invocation without modifying `pyproject.toml`.
- `uv run --only-group dev <cmd>` — run with only a specific dep group, excluding core deps.
- `uv sync --upgrade --all-groups` — upgrade all deps to latest compatible versions.

## Scripts

**`scripts/`** contains standalone helper scripts for common DevOps-type tasks any developer on the project may need
(e.g., code generation, release prep, data migration). Create scripts sparingly — only for repeated workflows that don't
fit neatly into a `make` target or one-liner.

**Conventions:**

- Start every script with a [uv script header](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies)
  (`# /// script` block) declaring `requires-python` and any `dependencies`. This lets anyone run the script with
  `uv run scripts/foo.py` without installing extras into the project.
- Use **Typer** for CLI argument parsing — it gives you `--help` for free with minimal boilerplate.
- Use **Rich** for pretty terminal output (tables, progress bars, coloured status messages).
- Keep scripts focused: one script, one job. If a script grows complex, it probably belongs in the library or a Makefile
  target instead.

## README Feature Matrix

Keep the feature matrix in `README.md` in sync. Update after finishing apply or archiving a change — set status to
`Available` with spec link (e.g., `[Available](openspec/specs/feature/)`). Only add rows for major library pillars
(parse, deparse, normalize, split, etc.), not minor helpers. Don't update during intermediate steps.
