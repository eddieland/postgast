## MODIFIED Requirements

### Requirement: Platform-aware library resolution

The module SHALL resolve the correct shared library for the current platform using a two-step search:

1. First, look for a vendored copy adjacent to the `_native.py` module (`libpg_query.so` on Linux, `libpg_query.dylib`
   on macOS, `pg_query.dll` on Windows).
2. If no vendored copy is found, fall back to `ctypes.util.find_library("pg_query")` for system-installed libraries.

#### Scenario: Load vendored library on Linux

- **WHEN** the module is imported on a Linux system
- **AND** `libpg_query.so` exists in the package directory
- **THEN** it loads the vendored `libpg_query.so`

#### Scenario: Load vendored library on macOS

- **WHEN** the module is imported on a macOS system
- **AND** `libpg_query.dylib` exists in the package directory
- **THEN** it loads the vendored `libpg_query.dylib`

#### Scenario: Load vendored library on Windows

- **WHEN** the module is imported on a Windows system
- **AND** `pg_query.dll` exists in the package directory
- **THEN** it loads the vendored `pg_query.dll`

#### Scenario: Fall back to system library

- **WHEN** the module is imported on any platform
- **AND** no vendored library exists in the package directory
- **THEN** it falls back to `ctypes.util.find_library("pg_query")`

#### Scenario: Load on Linux without vendored copy

- **WHEN** the module is imported on a Linux system
- **AND** no vendored `libpg_query.so` exists in the package directory
- **AND** libpg_query is installed system-wide
- **THEN** it loads the system `libpg_query.so` via `ctypes.util.find_library`

### Requirement: Library load failure raises clear error

The module SHALL raise an OSError with a descriptive message if libpg_query cannot be found via either the vendored path
or the system library search.

#### Scenario: Library not installed

- **WHEN** no vendored library exists in the package directory
- **AND** libpg_query is not installed on the system
- **THEN** an OSError is raised with a message indicating the library was not found
