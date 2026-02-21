## Context

postgast uses ctypes to call libpg_query's C functions. Today, `_native.py` calls `ctypes.util.find_library("pg_query")`
which searches system library paths. Users must install libpg_query separately and configure `LD_LIBRARY_PATH` /
`DYLD_LIBRARY_PATH`. This makes adoption painful — `pip install postgast` alone is not sufficient.

The project currently produces pure-Python wheels (`py3-none-any`) with zero dependencies. The build system is hatchling
with uv-dynamic-versioning for git-tag-based versions.

## Goals / Non-Goals

**Goals:**

- `pip install postgast` works out of the box on Linux (x86_64, aarch64), macOS (x86_64, arm64), and Windows (x86_64)
- The vendored library is compiled from libpg_query source during wheel build — no pre-built binaries checked into the repo
- System-installed libpg_query remains a fallback, so users can override with their own build
- sdist includes the libpg_query source so users can build from source on unsupported platforms

**Non-Goals:**

- Supporting architectures beyond the five listed above (e.g., s390x, ppc64le)
- Providing a way to install libpg_query system-wide via postgast
- Bundling multiple libpg_query versions or allowing version selection at runtime
- Windows ARM64 support (no GitHub-hosted runners available)

## Decisions

### 1. Vendor libpg_query source as a git submodule at `vendor/libpg_query`

**Choice**: Git submodule pinned to a release tag (e.g., `17-6.0.0`).

**Why over alternatives**:

- *Copying source into repo*: Harder to update, clutters git history with thousands of C files.
- *Downloading at build time*: Requires network access during build, breaks reproducibility.
- *Pre-built binaries in repo*: Platform matrix explosion, trust/provenance concerns.

A submodule tracks upstream cleanly and `git submodule update --init` is well-supported by CI and cibuildwheel.

### 2. Custom hatchling build hook (`hatch_build.py`) to compile and bundle the library

**Choice**: A `hatch_build.py` file at the project root implementing `BuildHookInterface`.

The hook will:

1. Run `make build_shared` (Linux/macOS) or the equivalent Windows build in `vendor/libpg_query/`
2. Determine the platform-appropriate library filename (`.so`, `.dylib`, `.dll`)
3. Inject it into the wheel via `build_data['force_include']` mapping to `postgast/<libname>`
4. Set `build_data['infer_tag'] = True` and `build_data['pure_python'] = False` for correct wheel platform tags

**Why over alternatives**:

- *hatch-build-scripts plugin*: Cannot set `infer_tag`/`pure_python` in build_data; no per-platform command variants.
- *CIBW_BEFORE_BUILD + static force-include*: `pyproject.toml` is static, can't conditionally include `.so` vs `.dylib`.
- *scikit-build-core*: Requires CMake; libpg_query ships a Makefile, not CMakeLists.txt. Overkill.

### 3. Library resolution: vendored-first with system fallback

**Choice**: `_native.py` loading logic becomes:

1. Look for the shared library adjacent to the `_native.py` file (`Path(__file__).parent / <libname>`)
2. If not found, fall back to `ctypes.util.find_library("pg_query")` (current behavior)
3. If neither found, raise `OSError` with an updated message

This keeps the existing system-library path working for users who install libpg_query themselves or develop against a
custom build.

### 4. Use cibuildwheel for cross-platform wheel production

**Choice**: cibuildwheel orchestrates builds inside manylinux containers (Linux), native macOS runners, and Windows
runners. Configuration lives in `pyproject.toml` under `[tool.cibuildwheel]`.

Target matrix:

| Platform | Architectures | Runner | Repair tool |
| --- | --- | --- | --- |
| Linux | x86_64, aarch64 | ubuntu-latest + QEMU | auditwheel |
| macOS | x86_64, arm64 | macos-13 (Intel), macos-14 (ARM) | delocate |
| Windows | AMD64 | windows-latest | delvewheel |

cibuildwheel handles calling `hatch build` (which triggers the build hook) and running the repair tools that ensure the
shared library is properly bundled and the wheel meets platform standards (manylinux, macOS delocate).

### 5. Publish workflow replaces pure-Python build with cibuildwheel matrix

**Choice**: The existing `.github/workflows/publish.yml` will be updated to:

1. Build wheels via cibuildwheel across the platform matrix
2. Build an sdist separately (includes vendor/ source for from-source builds)
3. Upload all artifacts and publish to PyPI

The CI workflow (`.github/workflows/ci.yml`) continues to test on Linux only for development speed.

### 6. sdist includes libpg_query source

**Choice**: Configure hatch to include `vendor/libpg_query/` in the sdist so that `pip install postgast` from source
(no wheel available) compiles libpg_query automatically via the same build hook.

## Risks / Trade-offs

**Wheel size increase** — Each platform wheel will include the compiled libpg_query (~2-4 MB). This is typical for
packages vendoring native libraries and acceptable for the UX improvement.
→ *Mitigation*: Only one platform's library is included per wheel.

**libpg_query build time in CI** — Compiling PostgreSQL parser source takes ~2-3 minutes per platform. aarch64 via QEMU
emulation may take 10+ minutes.
→ *Mitigation*: Only runs on publish (release tags), not on every PR. Can add build caching later if needed.

**Git submodule friction** — Contributors must `git submodule update --init` after cloning.
→ *Mitigation*: Document in CLAUDE.md/README. CI workflows use `submodules: true` in checkout.

**Windows build complexity** — libpg_query's Windows support uses `nmake /F Makefile.msvc` or may need MinGW. The build
hook must handle this path.
→ *Mitigation*: Test Windows builds in CI early. If Windows proves too difficult initially, ship without Windows wheels
and add later.

**auditwheel/delocate may flag libc dependencies** — The shared library links against libc, which auditwheel may try to
bundle.
→ *Mitigation*: libpg_query has no external dependencies beyond libc. auditwheel's manylinux policy already accounts
for libc. Should work out of the box.

## Open Questions

- **libpg_query version to pin**: Should we start with the latest release (`17-6.0.0`) or a specific known-good version?
- **Windows DLL strategy**: Does libpg_query's `Makefile.msvc` produce a proper DLL, or only a static `.lib`? May need
  to investigate building a shared library on Windows with MinGW instead.
- **aarch64 build strategy**: QEMU emulation is slow. Worth investigating GitHub's native ARM runners (now available in
  beta) or cross-compilation as alternatives?
