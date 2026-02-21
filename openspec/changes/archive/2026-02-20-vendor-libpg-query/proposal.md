## Why

postgast currently requires users to install libpg_query themselves and ensure it's on their library search path. This
makes `pip install postgast` insufficient — users must also compile or obtain the correct native library for their
platform. Vendoring pre-built libpg_query binaries into platform-specific wheels eliminates this friction and makes
postgast a true zero-setup package.

## What Changes

- Build platform-specific wheels that bundle the libpg_query shared library (`.so` on Linux, `.dylib` on macOS, `.dll`
  on Windows)
- Modify the library loading logic to first look for a vendored copy alongside the Python package before falling back to
  system-installed libraries
- Add a build pipeline (cibuildwheel or hatch build hook) that compiles libpg_query from source and places the artifact
  into the wheel
- Configure CI to produce wheels for Linux (manylinux), macOS (x86_64 + arm64), and Windows (x86_64)
- The existing fallback to system-installed libpg_query remains as a secondary resolution path

## Capabilities

### New Capabilities

- `vendored-library-bundling`: Compile libpg_query from source during wheel build and include the shared library in the
  wheel package data.

### Modified Capabilities

- `native-library-loading`: Library resolution must first check for a vendored copy bundled within the package before
  falling back to system library search paths.

## Impact

- **Code**: `src/postgast/_native.py` — loading logic updated to prefer vendored library
- **Build**: New build hook or build script to compile libpg_query and place the `.so`/`.dylib`/`.dll` into the wheel
- **CI**: `.github/workflows/publish.yml` updated to build platform-specific wheels across Linux/macOS/Windows and
  multiple Python versions
- **Packaging**: `pyproject.toml` updated with build hook config, wheel platform tags, and package data includes
- **Distribution**: Wheels become platform-specific (no longer pure Python); sdist still works for users who want to
  compile themselves
