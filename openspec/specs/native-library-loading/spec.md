# native-library-loading Specification

## Purpose

TBD - created by archiving change ctypes-library-loading. Update Purpose after archive.

## Requirements

### Requirement: Platform-aware library resolution

The module SHALL resolve the correct shared library filename for the current platform: `.so` on Linux, `.dylib` on
macOS, `.dll` on Windows.

#### Scenario: Load on Linux

- **WHEN** the module is imported on a Linux system
- **THEN** it attempts to load `libpg_query.so`

#### Scenario: Load on macOS

- **WHEN** the module is imported on a macOS system
- **THEN** it attempts to load `libpg_query.dylib`

#### Scenario: Load on Windows

- **WHEN** the module is imported on a Windows system
- **THEN** it attempts to load `pg_query.dll`

### Requirement: Library load failure raises clear error

The module SHALL raise an OSError with a descriptive message if libpg_query cannot be found.

#### Scenario: Library not installed

- **WHEN** libpg_query is not installed on the system
- **THEN** an OSError is raised with a message indicating the library was not found
