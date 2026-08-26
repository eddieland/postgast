# CLAUDE.md

## Project Overview

postgast is a BSD-licensed Python library that parses, deparses, normalizes, fingerprints, splits, and scans PostgreSQL
SQL. It binds to [libpg_query](https://github.com/pganalyze/libpg_query) via `ctypes`. It uses no Cython, Rust, or C
extensions. It deserializes results into protobuf Python objects.

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

- `src/postgast/`: package source (hatchling, `packages = ["src/postgast"]`)
- `tests/`: pytest test directory
- `uv` manages dependencies. `hatchling` builds the package. The version comes from git tags (`uv-dynamic-versioning`).
- `__init__.py`: re-exports that define the public API
- The package uses the official `protobuf` library.

## Conventions

- New modules: plain names (`split.py`), not underscore-prefixed.
- The `__init__.py` re-exports and `__all__` define the public API. Module prefixes do not.
- Annotate module-level constants with `typing.Final` (e.g., `TIMEOUT: Final = 30`). No automated rule enforces this yet
  ([ruff#10137](https://github.com/astral-sh/ruff/issues/10137)). Treat it as a manual convention.
- Ruff: line-length 120, Google-style docstrings. Type checker: BasedPyright. Python 3.10+.
- Always use `uv run`. Never use bare `pip install` or manual venv activation.
- `uv add <pkg>` adds a core dependency. Keep the core list small.
- `uv add --dev <pkg>` adds a dev dependency. `uv add --group recipes <pkg>` and `uv add --group docs <pkg>` add to the
  recipes group and the docs group.
- `uv run --with <pkg> <cmd>` adds a package for a single invocation. It does not modify `pyproject.toml`.
- `uv run --only-group dev <cmd>` runs with one dependency group and excludes the core dependencies.
- `uv sync --upgrade --all-groups` upgrades all dependencies to the latest compatible versions.

## Documentation Style

This style applies to every piece of prose the project produces. That includes documentation, docstrings, OpenSpec
artifacts, commit messages, PR titles and bodies, and review comments. It does not apply to code, identifiers, or quoted
tool output.

The rules below follow the principles of ASD-STE100 (Simplified Technical English), applied informally. The rules are
authoritative. Write for readers whose first language is not English. Fix prose that breaks a rule when you edit the
file that holds it.

**Do:**

- Write one idea per sentence. Keep each sentence under 20 words.
- Use active voice and present tense.
- Use the same term for the same concept every time.
- Use concrete nouns. Name the file, the function, the table, or the service.

**Do not:**

- Use a dash (em dash, en dash, or hyphen) as punctuation between clauses. Use a period, a comma, or parentheses
  instead. A hyphen inside a compound word is fine.
- Use idioms. Write the literal meaning. A non-native speaker may not recognize the idiom.
- Use phrasal verbs. Write "start" instead of "spin up" and "remove" instead of "tear down". Write "deploy" instead of
  "roll out" and "use" instead of "fall back on".
- Use evaluative adjectives such as robust, elegant, seamless, comprehensive, powerful, significant, critical, or clean.
- Use the patterns "not just X, but Y" and "it's not X, it's Y".
- Write a three-item list for rhythm. Every item must carry content.
- Open with filler such as "This ticket aims to", "In order to", or "As part of our ongoing effort". State the point
  first.

## Scripts

**`scripts/`** holds standalone helper scripts for common DevOps tasks that any developer on the project may need.
Examples are code generation, release preparation, and data migration. Create scripts sparingly. Add one only for a
repeated workflow that does not fit a `make` target or a one-liner.

**Conventions:**

- Start every script with a [uv script header](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies)
  (`# /// script` block) that declares `requires-python` and any `dependencies`. Anyone can then run the script with
  `uv run scripts/foo.py` without installing extras into the project.
- Use **Typer** for CLI argument parsing. Typer generates `--help` with little extra code.
- Use **Rich** for terminal output such as tables, progress bars, and coloured status messages.
- Keep scripts focused: one script, one job. A script that grows large belongs in the library or in a Makefile target.

## cibuildwheel Test Dependencies

`[tool.cibuildwheel]` in `pyproject.toml` has its own `test-requires` list, separate from the `test` dependency group.
Add every new test dependency to **both** lists: `[dependency-groups] test` and `test-requires` under
`[tool.cibuildwheel]`. Otherwise the publish workflow wheel tests fail with `ModuleNotFoundError`.

## README Feature Matrix

Keep the feature matrix in `README.md` current. Update the matrix after you finish apply or archive a change. Set the
status to `Available` and add a spec link (e.g., `[Available](openspec/specs/feature/)`). Add rows only for the main
library features (parse, deparse, normalize, split). Do not add rows for small helpers. Do not update the matrix during
intermediate steps.
