## Why

The CI pipeline (`ci.yml`) only tests on ubuntu-latest with two Python versions (3.10, 3.14). Since postgast ships a
compiled native library (`libpg_query`) via ctypes — with platform-specific shared objects (`.so`, `.dylib`) — untested
platforms risk shipping broken wheels. The publish workflow already builds wheels for macOS and Windows via
cibuildwheel, but those wheels are never tested in CI before release.

## What Changes

- Expand the CI OS matrix to include macOS and Windows alongside Linux
- Uncomment and enable the full Python version matrix (3.10–3.14)
- Split the CI workflow into separate lint and test jobs so linting runs once (Linux-only) while tests run across the
  full OS/Python matrix
- Handle platform-specific native library build differences (`.so` on Linux, `.dylib` on macOS, `.dll` on Windows)
- Ensure coverage upload only happens once (single matrix entry)

## Capabilities

### New Capabilities

- `ci-pipeline`: Specifies the CI workflow structure, matrix strategy, job separation, and platform-specific build
  requirements

### Modified Capabilities

None — this change is CI infrastructure only. No library behavior or API requirements change.

## Impact

- `.github/workflows/ci.yml` — primary file being reworked (matrix expansion, job split)
- `Makefile` — may need Windows-compatible build-native support (currently only handles `.so` and `.dylib`)
- `vendor/libpg_query/` — native library build must succeed on all target platforms
- `src/postgast/` — native library loading (`_native.py`) must handle `.dll` on Windows if not already
