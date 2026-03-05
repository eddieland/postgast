# postgast

[![PyPI](https://img.shields.io/pypi/v/postgast)](https://pypi.org/project/postgast/)
[![Python](https://img.shields.io/pypi/pyversions/postgast)](https://pypi.org/project/postgast/)
[![License](https://img.shields.io/pypi/l/postgast)](https://github.com/eddieland/postgast/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/eddieland/postgast/ci.yml?label=CI)](https://github.com/eddieland/postgast/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/eddieland/postgast/graph/badge.svg)](https://codecov.io/gh/eddieland/postgast)
[![Docs](https://readthedocs.org/projects/postgast/badge/?version=latest)](https://postgast.readthedocs.io)
[![Downloads](https://img.shields.io/pypi/dm/postgast)](https://pypi.org/project/postgast/)

BSD-licensed Python bindings to [libpg_query](https://github.com/pganalyze/libpg_query), the real PostgreSQL parser
extracted as a standalone C library by [pganalyze](https://pganalyze.com/).

`libpg_query` is the foundation of this library. It contains the actual PostgreSQL parser source code, pulled directly
from the PostgreSQL codebase and packaged so it can be used outside the server. Every operation postgast provides
(parsing, deparsing, normalization, fingerprinting, splitting, and scanning) is performed by calling into
`libpg_query`'s C functions. This means postgast always produces the same parse tree that PostgreSQL itself would, with
full coverage of PostgreSQL syntax, not a hand-written approximation.

Only two runtime dependencies are needed: `protobuf` (for deserializing parse results) and the vendored `libpg_query`
shared library itself.

<p align="center">
  <img src="https://raw.githubusercontent.com/eddieland/postgast/main/docs/logo.png" width="350" alt="postgast logo"/>
</p>

## Features

| Feature          | Status                                      | Description                                                                |
| ---------------- | ------------------------------------------- | -------------------------------------------------------------------------- |
| **Parse**        | [Available](openspec/specs/operations/)     | SQL text to protobuf AST                                                   |
| **Deparse**      | [Available](openspec/specs/operations/)     | AST back to SQL text                                                       |
| **Normalize**    | [Available](openspec/specs/operations/)     | Replace constants with parameter placeholders                              |
| **Fingerprint**  | [Available](openspec/specs/operations/)     | Identify structurally equivalent statements                                |
| **Split**        | [Available](openspec/specs/operations/)     | Split multi-statement strings (respects strings, comments, dollar-quoting) |
| **Scan**         | [Available](openspec/specs/operations/)     | Tokenize SQL with keyword classification                                   |
| **Tree Walking** | [Available](openspec/specs/ast-navigation/) | Walk/visit AST nodes with depth-first traversal and visitor pattern        |
| **AST Helpers**  | [Available](openspec/specs/ast-navigation/) | Extract tables, columns, functions; generate DROP from CREATE DDL          |
| **Pretty Print** | [Available](openspec/specs/pretty-print/)   | Rudimentary SQL formatting via AST round-trip (strips comments)            |

Built on `libpg_query` 17-latest (PostgreSQL 17 parser).

## Installation

```bash
pip install postgast
```

## Quick Start

```python
import postgast

# Parse a query into an AST
tree = postgast.parse("SELECT id, name FROM users WHERE active = true")

# Deparse an AST back to SQL
sql = postgast.deparse(tree)

# Normalize a query (replace constants with placeholders)
normalized = postgast.normalize("SELECT * FROM users WHERE id = 42")
# => "SELECT * FROM users WHERE id = $1"

# Fingerprint a query
fp = postgast.fingerprint("SELECT * FROM users WHERE id = 42")

# Split a multi-statement string
stmts = postgast.split("SELECT 1; SELECT 2;")
# => ["SELECT 1", "SELECT 2"]
```

## Pretty Printing

`postgast` includes a rudimentary SQL pretty-printer via `format_sql`. It works by parsing SQL into a protobuf AST and
walking it back out with uppercase keywords, clause-per-line layout, and indented bodies:

```python
import postgast

formatted = postgast.format_sql("select id, name from users where active = true order by name")
print(formatted)
# SELECT
#   id,
#   name
# FROM
#   users
# WHERE
#   active = true
# ORDER BY
#   name;
```

**Caveats:** Because the formatter operates on the parsed AST, it strips comments. The PostgreSQL parser discards them
during parsing, so they are not present in the tree. Whitespace and stylistic choices from the original SQL are also not
preserved.

This is the area of the library most likely to evolve over time as our needs and user stories change. The current
implementation covers the common cases, but the formatting rules, output style, and supported syntax should be
considered unstable. If you depend on exact output, pin your version.

## Motivation

[pglast](https://github.com/lelit/pglast) is an excellent library that wraps `libpg_query` for Python, but it is
licensed under GPLv3, which makes it unusable in many commercial and permissively-licensed projects. `postgast` provides
a BSD-licensed alternative that leans directly on `libpg_query`'s C API via `ctypes`, keeping the implementation minimal
and the dependency footprint small.

## How It Works

`libpg_query` is included as a Git submodule under `vendor/libpg_query`. At build time, a custom hatchling build hook
compiles it into a platform-specific shared library (`libpg_query.so`, `.dylib`, or `.dll`) and bundles it inside the
wheel. Pre-built wheels are published to PyPI for common platforms, so most users never need a C compiler.

At runtime, `postgast` loads the vendored shared library and calls `libpg_query`'s C functions directly through Python's
`ctypes` module. Parse results come back as serialized protobuf, which postgast deserializes into Python objects using
the standard `protobuf` library. There is no Cython, no Rust, and no C extension module to compile, just a vendored
shared library and pure Python on top.

## License

BSD 2-Clause. See [LICENSE](LICENSE) for details.

`libpg_query` is licensed under the
[BSD 3-Clause License](https://github.com/pganalyze/libpg_query/blob/17-latest/LICENSE). Portions of the PostgreSQL
source code used by `libpg_query` are licensed under the
[PostgreSQL License](https://www.postgresql.org/about/licence/).
