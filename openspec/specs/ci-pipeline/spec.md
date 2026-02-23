### Requirement: CI workflow splits lint and test into separate jobs

The CI workflow (`.github/workflows/ci.yml`) SHALL define two top-level jobs: `lint` and `test`. The `test` job SHALL
depend on `lint` (via `needs: lint`) so that test matrix jobs only run after linting passes.

#### Scenario: Lint failure blocks tests

- **WHEN** the `lint` job fails (e.g., ruff finds a formatting issue)
- **THEN** no `test` matrix jobs SHALL start

#### Scenario: Lint passes, tests run

- **WHEN** the `lint` job succeeds
- **THEN** all `test` matrix jobs SHALL start in parallel

### Requirement: Lint job runs on Linux with a single Python version

The `lint` job SHALL run on `ubuntu-latest` with a single Python version. It SHALL execute all formatting, spelling,
linting, and type-checking steps: mdformat, codespell, ruff check, ruff format, and basedpyright.

#### Scenario: Lint job executes all checks

- **WHEN** the `lint` job runs
- **THEN** it SHALL execute mdformat, codespell, ruff check, ruff format --check, and basedpyright in sequence

#### Scenario: Lint job does not run tests

- **WHEN** the `lint` job runs
- **THEN** it SHALL NOT execute pytest or any test commands

### Requirement: Test job runs across OS and Python version matrix

The `test` job SHALL use a strategy matrix with:

- OS: `ubuntu-latest`, `macos-latest`, `windows-latest`
- Python: `3.10`, `3.11`, `3.12`, `3.13`, `3.14`

Each matrix combination SHALL run as a separate job using `runs-on: ${{ matrix.os }}`.

#### Scenario: Full matrix expansion

- **WHEN** the CI workflow triggers
- **THEN** the `test` job SHALL produce 15 matrix jobs (3 OSes × 5 Python versions)

#### Scenario: Matrix job uses correct runner

- **WHEN** a matrix job has `os: macos-latest` and `python-version: 3.12`
- **THEN** it SHALL run on a macOS runner with Python 3.12 installed

### Requirement: Test job builds native library with platform-appropriate method

The `test` job SHALL build the libpg_query native library before running tests. On Linux and macOS, it SHALL use
`make build-native`. On Windows, it SHALL use a different build method (e.g., `nmake /F Makefile.msvc` or
`uv build --wheel`) since the project Makefile does not support Windows.

#### Scenario: Linux/macOS native build

- **WHEN** a test matrix job runs on `ubuntu-latest` or `macos-latest`
- **THEN** it SHALL execute `make build-native` to compile and copy the shared library

#### Scenario: Windows native build

- **WHEN** a test matrix job runs on `windows-latest`
- **THEN** it SHALL NOT call `make build-native`
- **THEN** it SHALL use an alternative build method appropriate for Windows

### Requirement: Test job runs pytest on all matrix entries

Every `test` matrix job SHALL execute `uv run pytest` to run the test suite. Tests SHALL NOT include integration tests
(which require Docker/PostgreSQL).

#### Scenario: Tests execute on each platform

- **WHEN** a test matrix job completes the native library build
- **THEN** it SHALL run `uv run pytest` and report results

### Requirement: Coverage uploads from a single matrix entry

The CI workflow SHALL upload coverage data to Codecov from exactly one matrix entry: `ubuntu-latest` with Python `3.14`.
All other matrix entries SHALL skip the coverage upload step.

#### Scenario: Coverage upload on designated entry

- **WHEN** the test matrix job for `ubuntu-latest` + Python `3.14` completes
- **THEN** it SHALL run pytest with `--cov --cov-report=xml` and upload `coverage.xml` to Codecov

#### Scenario: Coverage skipped on other entries

- **WHEN** a test matrix job runs on any OS/Python combination other than `ubuntu-latest` + `3.14`
- **THEN** it SHALL NOT upload coverage data to Codecov

### Requirement: Workflow triggers on push and PR to main branches

The CI workflow SHALL trigger on `push` to `main` and `master` branches, and on `pull_request` targeting `main` and
`master` branches. This matches the existing trigger configuration.

#### Scenario: PR triggers CI

- **WHEN** a pull request is opened targeting the `main` branch
- **THEN** both the `lint` and `test` jobs SHALL run

#### Scenario: Push triggers CI

- **WHEN** a commit is pushed to the `main` branch
- **THEN** both the `lint` and `test` jobs SHALL run

### Requirement: Submodules are checked out for native library build

All jobs that build the native library SHALL checkout the repository with `submodules: true` and `fetch-depth: 0` to
ensure the `vendor/libpg_query` submodule is available and git-tag-based versioning works.

#### Scenario: Submodule available in test job

- **WHEN** a `test` matrix job starts
- **THEN** the `vendor/libpg_query/` directory SHALL exist and contain the libpg_query source code
