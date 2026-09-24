# vendored-library-bundling Specification

## Purpose

Compile libpg_query from vendored source during wheel build and bundle the shared library in the wheel, enabling
zero-setup installation via `pip install postgast`.

## Requirements

### Requirement: libpg_query source vendored as git submodule

The project SHALL include the libpg_query source code as a git submodule at `vendor/libpg_query/`, pinned to a specific
release tag.

#### Scenario: Fresh clone includes submodule reference

- **WHEN** a developer clones the repository with `--recurse-submodules`
- **THEN** the `vendor/libpg_query/` directory contains the libpg_query source at the pinned version

### Requirement: Build hook compiles libpg_query during wheel build

The build system SHALL compile libpg_query from source during `hatch build` (or equivalent wheel build) using a custom
hatchling build hook. The hook SHALL produce the platform-appropriate shared library and include it in the wheel.

#### Scenario: Build wheel on Linux

- **WHEN** `hatch build -t wheel` runs on a Linux system
- **THEN** the hook runs `make build_shared` in `vendor/libpg_query/`
- **AND** the resulting `libpg_query.so` is included in the wheel at `postgast/libpg_query.so`

#### Scenario: Build wheel on macOS

- **WHEN** `hatch build -t wheel` runs on a macOS system
- **THEN** the hook runs `make build_shared` in `vendor/libpg_query/`
- **AND** the resulting `libpg_query.dylib` is included in the wheel at `postgast/libpg_query.dylib`

#### Scenario: Build wheel on Windows

- **WHEN** `hatch build -t wheel` runs on a Windows system
- **THEN** the hook compiles libpg_query using the appropriate Windows build command
- **AND** the resulting DLL is included in the wheel at `postgast/pg_query.dll`

### Requirement: Wheel uses platform-specific tags

The build hook SHALL set `infer_tag = True` and `pure_python = False` in build data so that the resulting wheel has
correct platform-specific tags (e.g., `manylinux_2_17_x86_64`, `macosx_14_0_arm64`) instead of `py3-none-any`.

#### Scenario: Built wheel has platform tag

- **WHEN** a wheel is built on any platform
- **THEN** the wheel filename contains a platform-specific tag, not `none-any`

### Requirement: sdist includes libpg_query source

The sdist SHALL include the `vendor/libpg_query/` directory so that users installing from source (no pre-built wheel)
can compile libpg_query via the same build hook.

#### Scenario: Install from sdist

- **WHEN** a user runs `pip install postgast` on a platform without a pre-built wheel
- **THEN** pip falls back to the sdist, compiles libpg_query from the vendored source, and installs successfully

### Requirement: sdist holds no compiled artifacts

The sdist SHALL hold only source files. The build hook SHALL do nothing for the sdist target. The sdist SHALL exclude
object files, static libraries, and shared libraries. The sdist SHALL include every file that the libpg_query build
needs, including the headers under `src/postgres/include/lib/`.

#### Scenario: Build sdist after a local native build

- **WHEN** `uv build --sdist` runs in a checkout where `vendor/libpg_query` holds `.o` files and `libpg_query.so`
- **THEN** the sdist contains no `.o`, `.a`, `.so`, `.dylib`, or `.dll` files

#### Scenario: Build from sdist on another architecture

- **WHEN** piwheels builds the sdist on armv7l
- **THEN** `make build_shared` compiles every object for armv7l and links the shared library

### Requirement: CI builds wheels for target platform matrix

The CI publish workflow SHALL use cibuildwheel to produce wheels for:

- Linux: x86_64, aarch64, and armv7l (manylinux and musllinux)
- macOS: x86_64 and arm64
- Windows: AMD64 and ARM64

#### Scenario: Release publishes platform wheels

- **WHEN** a release is published on GitHub
- **THEN** cibuildwheel builds wheels for all seven platform/architecture combinations
- **AND** all wheels are uploaded to PyPI
