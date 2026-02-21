## 1. Extract lint job from existing build job

- [ ] 1.1 Create a `lint` job in `ci.yml` that runs on `ubuntu-latest` with a single Python version
- [ ] 1.2 Move mdformat, codespell, ruff check, ruff format, and basedpyright steps into the `lint` job
- [ ] 1.3 Remove lint/format/type-check steps from the old `build` job (which becomes the `test` job)

## 2. Create test job with OS and Python matrix

- [ ] 2.1 Rename the existing `build` job to `test` and add `needs: lint` dependency
- [ ] 2.2 Expand OS matrix to `["ubuntu-latest", "macos-latest", "windows-latest"]`
- [ ] 2.3 Expand Python matrix to `["3.10", "3.11", "3.12", "3.13", "3.14"]`
- [ ] 2.4 Keep `runs-on: ${{ matrix.os }}` (already present)

## 3. Handle platform-specific native library build

- [ ] 3.1 Add conditional step: run `make build-native` only when `runner.os != 'Windows'`
- [ ] 3.2 Add Windows-specific build step using `nmake /F Makefile.msvc` in `vendor/libpg_query` or `uv build --wheel`
- [ ] 3.3 Ensure checkout step includes `submodules: true` and `fetch-depth: 0` in both jobs

## 4. Configure coverage upload for single matrix entry

- [ ] 4.1 Add conditional `if` on coverage pytest step: only run `--cov --cov-report=xml` on `ubuntu-latest` + Python
  `3.14`
- [ ] 4.2 Add conditional `if` on Codecov upload step matching the same matrix entry
- [ ] 4.3 Run plain `uv run pytest` (without coverage flags) on all other matrix entries

## 5. Validate the workflow

- [ ] 5.1 Run `actionlint` or manually review the updated `ci.yml` for YAML syntax and GitHub Actions expression
  correctness
- [ ] 5.2 Verify the workflow triggers (`push` and `pull_request` on `main`/`master`) are preserved
