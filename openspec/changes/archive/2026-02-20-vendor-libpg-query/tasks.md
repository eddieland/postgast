## 1. Vendor libpg_query source

- [x] 1.1 Add libpg_query as a git submodule at `vendor/libpg_query` pinned to the latest release tag
- [x] 1.2 Add `vendor/` to hatch sdist includes so source distributions contain the submodule contents
- [x] 1.3 Update `.gitignore` to allow the `vendor/` directory while still ignoring build artifacts within it

## 2. Build hook

- [x] 2.1 Create `hatch_build.py` implementing `BuildHookInterface` with `initialize()` that compiles libpg_query via `make build_shared` (Linux/macOS) and includes the shared library via `build_data['force_include']`
- [x] 2.2 Set `build_data['infer_tag'] = True` and `build_data['pure_python'] = False` in the hook for platform-specific wheel tags
- [x] 2.3 Add `[tool.hatch.build.hooks.custom]` to `pyproject.toml` to register the build hook
- [x] 2.4 Handle Windows build path in the hook (investigate `Makefile.msvc` / MinGW for DLL production)
- [x] 2.5 Implement `clean()` method to remove compiled artifacts
- [x] 2.6 Verify `uv build` produces a platform-tagged wheel with the shared library inside

## 3. Library loading

- [x] 3.1 Update `_load_libpg_query()` in `src/postgast/_native.py` to first check for a vendored library at `Path(__file__).parent / <platform-lib-name>` before falling back to `ctypes.util.find_library`
- [x] 3.2 Update the `OSError` message to reflect that the vendored library is also checked
- [x] 3.3 Add unit tests for vendored-first loading (mock the file existence check and ctypes.CDLL)
- [x] 3.4 Add unit test for fallback to system library when no vendored copy exists
- [x] 3.5 Add unit test for OSError when neither vendored nor system library is found

## 4. CI and publishing

- [x] 4.1 Add `[tool.cibuildwheel]` configuration to `pyproject.toml` targeting Linux (x86_64, aarch64), macOS (x86_64, arm64), and Windows (AMD64)
- [x] 4.2 Update `.github/workflows/publish.yml` to build wheels via cibuildwheel across the platform matrix and build sdist separately
- [x] 4.3 Add QEMU setup step for Linux aarch64 cross-architecture builds
- [x] 4.4 Ensure CI checkout steps use `submodules: true` to fetch the vendored source
- [x] 4.5 Update `.github/workflows/ci.yml` checkout to include submodules for test runs

## 5. Packaging metadata

- [x] 5.1 Update `pyproject.toml` classifiers to remove `"Operating System :: OS Independent"` (wheels are now platform-specific)
- [x] 5.2 Update project description in `pyproject.toml` to reflect that libpg_query is bundled

## 6. Validation

- [x] 6.1 Build a wheel locally and verify the shared library is present inside the wheel archive
- [x] 6.2 Install the locally-built wheel in a clean virtualenv and verify `import postgast` works without system libpg_query
- [x] 6.3 Verify system-library fallback still works when the vendored copy is absent
