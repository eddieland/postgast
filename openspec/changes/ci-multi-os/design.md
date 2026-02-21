## Context

The CI workflow (`.github/workflows/ci.yml`) currently runs a single monolithic job on `ubuntu-latest` with Python 3.10
and 3.14. The publish workflow already builds wheels for Linux, macOS (x86_64 + ARM), and Windows via cibuildwheel, but
these platforms are never tested in CI until release time.

The project has existing cross-platform support in its build tooling:

- `hatch_build.py` compiles libpg_query and bundles the platform-specific shared library (`.so`, `.dylib`, `.dll`)
- `src/postgast/_native.py` loads the correct library for Linux, macOS, and Windows
- `vendor/libpg_query/` has `Makefile` (Linux/macOS) and `Makefile.msvc` (Windows) — though the MSVC makefile currently
  only produces a static `pg_query.lib`, not a `pg_query.dll`
- `pyproject.toml` has cibuildwheel config targeting all three platforms

The dev `Makefile` only handles Linux/macOS (`make build-native`); CI on Windows will use hatch/cibuildwheel build paths
instead.

## Goals / Non-Goals

**Goals:**

- Test on Linux, macOS, and Windows in CI for every push/PR to main
- Test across Python 3.10–3.14 on all platforms
- Run linting/formatting once (not duplicated per OS/Python combination)
- Keep CI wall-clock time reasonable by parallelizing lint and test jobs
- Upload coverage from a single matrix entry

**Non-Goals:**

- Fixing the Windows native build (the `Makefile.msvc` → `.dll` gap) — that's a separate change if Windows CI fails
- ARM/aarch64 CI runners (GitHub doesn't offer free ARM runners; cross-platform coverage is handled by cibuildwheel at
  publish time)
- Modifying the publish workflow
- Adding integration tests (Docker-based PostgreSQL tests) to multi-OS CI

## Decisions

### 1. Split into lint + test jobs

**Decision:** Separate the single `build` job into two jobs: `lint` (Linux-only, single Python version) and `test` (full
OS × Python matrix).

**Rationale:** Linting (ruff, mdformat, codespell, basedpyright) is platform-independent and only needs to run once.
Running it in every matrix cell wastes ~15 matrix slots worth of CI minutes. The `test` job depends on `lint` passing
first, providing a fast-fail gate.

**Alternative considered:** Keep a single job with conditional steps. Rejected because it still wastes runner time
starting up environments just to skip steps.

### 2. OS matrix: ubuntu-latest, macos-latest, windows-latest

**Decision:** Use `ubuntu-latest`, `macos-latest`, and `windows-latest`.

**Rationale:** These are the GitHub-hosted runner defaults. `macos-latest` is ARM (M-series) which matches the primary
macOS target. The publish workflow covers macos-13 (Intel) separately via cibuildwheel. Using `-latest` tags keeps CI
current without manual runner version bumps.

**Alternative considered:** Pin specific runner versions (e.g., `ubuntu-22.04`). Rejected — postgast doesn't have
OS-version-sensitive behavior, and `-latest` reduces maintenance.

### 3. Python matrix: 3.10, 3.11, 3.12, 3.13, 3.14

**Decision:** Enable the full range of supported Python versions (currently commented out in ci.yml).

**Rationale:** The `pyproject.toml` declares `requires-python = ">=3.10"` and cibuildwheel builds for 3.10–3.14. CI
should validate all supported versions.

### 4. Build native library via Make on Linux/macOS, skip or use hatch on Windows

**Decision:** The `test` job runs `make build-native` on Linux and macOS. On Windows, use
`uv run python -c "from postgast._native import _load_libpg_query; _load_libpg_query()"` or let pytest trigger the load
— if the build hook works, tests pass; if not, they fail with a clear error.

**Rationale:** The dev `Makefile` doesn't support Windows and adding `nmake` support to it is out of scope. The
`hatch_build.py` hook already calls `nmake /F Makefile.msvc` and is the canonical Windows build path. For CI testing, we
can either:

- (a) Run `uv build --wheel` to trigger the hatch build hook, then install and test
- (b) Call `nmake` directly in CI, similar to what `hatch_build.py` does

Option (a) is simpler and uses the same path as users. If Windows CI fails due to the `.dll` gap, that's a signal to fix
`Makefile.msvc` in a separate change.

### 5. Coverage upload from a single matrix entry

**Decision:** Upload coverage only from the `ubuntu-latest` + `python 3.14` entry (matching current behavior).

**Rationale:** Codecov only needs one coverage report. Uploading from multiple entries creates merge noise without
benefit.

## Risks / Trade-offs

**Windows CI may fail initially** → The `Makefile.msvc` only produces a static `.lib`, not a `.dll`. The hatch build
hook expects `pg_query.dll`. If this causes test failures on Windows, we can either fix `Makefile.msvc` as a follow-up
or temporarily exclude Windows from the matrix. This is acceptable — the CI change surfaces the problem rather than
hiding it.

**CI time increases** → A 3 OS × 5 Python matrix = 15 test jobs (up from 2). Mitigated by running lint separately as a
fast gate, and GitHub Actions runs matrix jobs in parallel. Expected wall-clock time stays under 10 minutes.

**macOS runner minutes cost more** → GitHub charges 10x for macOS minutes on private repos. Not a concern for open
source repos (free tier), but worth noting if the repo goes private.
