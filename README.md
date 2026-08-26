# `postgast`

[![PyPI](https://img.shields.io/pypi/v/postgast)](https://pypi.org/project/postgast/)
[![Python](https://img.shields.io/pypi/pyversions/postgast)](https://pypi.org/project/postgast/)
[![License](https://img.shields.io/pypi/l/postgast)](https://github.com/eddieland/postgast/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/eddieland/postgast/ci.yml?label=CI)](https://github.com/eddieland/postgast/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/eddieland/postgast/graph/badge.svg)](https://codecov.io/gh/eddieland/postgast)
[![Docs](https://readthedocs.org/projects/postgast/badge/?version=latest)](https://postgast.readthedocs.io)
[![Downloads](https://img.shields.io/pypi/dm/postgast)](https://pypi.org/project/postgast/)

BSD-licensed Python bindings to [libpg_query](https://github.com/pganalyze/libpg_query). `libpg_query` is the PostgreSQL
parser, packaged as a standalone C library by [pganalyze](https://pganalyze.com/).

`libpg_query` holds the PostgreSQL parser source code. pganalyze copies that code from the PostgreSQL codebase and
packages it to run outside the PostgreSQL server. Every `postgast` operation calls a `libpg_query` C function. Parse,
deparse, normalize, fingerprint, split, and scan all work this way. `postgast` returns the same parse tree that
PostgreSQL builds, and it accepts the same syntax. `postgast` does not reimplement the grammar.

`postgast` declares one runtime dependency, `protobuf`, which deserializes parse results. The vendored `libpg_query`
shared library ships inside the wheel. Any `protobuf` release from 5.29 onward works, across major versions. You never
need `protoc`. `postgast` builds its message classes at import time from a descriptor set that it ships.

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

`postgast` uses `libpg_query` 18.0.0, the PostgreSQL 18 parser.

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

`format_sql` is a basic SQL pretty-printer. It parses the SQL into a protobuf AST. It then renders that AST as text with
uppercase keywords, one clause per line, and indented bodies:

```python
import postgast

formatted = postgast.format_sql("select id, name from users where active = true order by name")
print(formatted)
# SELECT id, name
# FROM users
# WHERE active = TRUE
# ORDER BY name;
```

**Caveats:** The formatter reads the parsed AST, so it removes comments. The PostgreSQL parser discards comments, so the
tree never holds them. The formatter also discards the whitespace and the layout of the original SQL.

The formatter changes more often than the rest of the library. It handles the common cases today. Treat the formatting
rules, the output style, and the supported syntax as unstable. Pin your `postgast` version if you depend on the exact
output.

## Motivation

[pglast](https://github.com/lelit/pglast) also wraps `libpg_query` for Python. `pglast` uses the GPLv3 license. That
license blocks `pglast` from many commercial projects and from many permissively licensed projects. `postgast` is a
BSD-licensed alternative. It calls the `libpg_query` C API through `ctypes`. This keeps the code small and the
dependency list short.

## How It Works

`postgast` vendors `libpg_query` as a Git submodule under `vendor/libpg_query`. A hatchling build hook compiles that
submodule at build time. The hook produces a platform-specific shared library (`libpg_query.so`, `.dylib`, or `.dll`)
and places it inside the wheel. PyPI carries pre-built wheels for the common platforms, so most users need no C
compiler.

At runtime, `postgast` loads the vendored shared library. It calls the `libpg_query` C functions through Python's
`ctypes` module. `libpg_query` returns each parse result as serialized protobuf. `postgast` deserializes that result
into Python objects with the `protobuf` library. The package compiles no Cython, no Rust, and no C extension module. It
ships one vendored shared library and pure Python code.

`postgast` does not ship `protoc` gencode. It ships the schema as a serialized descriptor set (`pg_query.desc`). It
builds the message classes from that file at import time, using the public protobuf descriptor APIs. Gencode carries a
version gate. The gate refuses to import on any `protobuf` runtime older than the `protoc` that produced the gencode. A
descriptor set has no such gate. A `postgast` release therefore works across `protobuf` major versions, and installing
it never requires `protoc`.

## License

BSD 2-Clause. See [LICENSE](LICENSE) for details.

`libpg_query` is licensed under the
[BSD 3-Clause License](https://github.com/pganalyze/libpg_query/blob/18-latest/LICENSE). Portions of the PostgreSQL
source code used by `libpg_query` are licensed under the
[PostgreSQL License](https://www.postgresql.org/about/licence/).
