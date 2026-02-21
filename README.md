# postgast

BSD-licensed Python bindings to [libpg_query](https://github.com/pganalyze/libpg_query), the PostgreSQL parser extracted
as a standalone C library.

Parse, deparse, normalize, fingerprint, and split PostgreSQL SQL statements from Python with zero dependencies beyond
the vendored C library.

## Features

| Feature          | Status                                       | Description                                                                |
| ---------------- | -------------------------------------------- | -------------------------------------------------------------------------- |
| **Parse**        | [Available](openspec/specs/parse/)           | SQL text to protobuf AST                                                   |
| **Deparse**      | [Available](openspec/specs/deparse/)         | AST back to SQL text                                                       |
| **Normalize**    | [Available](openspec/specs/normalize/)       | Replace constants with parameter placeholders                              |
| **Fingerprint**  | [Planned](openspec/changes/add-fingerprint/) | Identify structurally equivalent statements                                |
| **Split**        | [Planned](openspec/changes/split/)           | Split multi-statement strings (respects strings, comments, dollar-quoting) |
| **Scan**         | [Planned](openspec/changes/scan-tokenize/)   | Tokenize SQL with keyword classification                                   |
| **Tree Walking** | [Available](openspec/specs/tree-walking/)    | Walk/visit AST nodes with depth-first traversal and visitor pattern        |

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

## Motivation

[pglast](https://github.com/lelit/pglast) is an excellent library that wraps `libpg_query` for Python, but it is
licensed under GPLv3, which makes it unusable in many commercial and permissively-licensed projects. `postgast` provides
a BSD-licensed alternative that leans directly on `libpg_query`'s C API via `ctypes`, keeping the implementation minimal
and the dependency footprint small.

## How It Works

`postgast` calls `libpg_query`'s C functions directly through Python's `ctypes` module. Parse results are returned as
protobuf messages, deserialized into Python objects. There is no Cython, no Rust, and no C extension module to compile —
just a vendored shared library and pure Python on top.

## License

BSD 2-Clause. See [LICENSE](LICENSE) for details.

`libpg_query` is licensed under the
[BSD 3-Clause License](https://github.com/pganalyze/libpg_query/blob/17-latest/LICENSE). Portions of the PostgreSQL
source code used by `libpg_query` are licensed under the
[PostgreSQL License](https://www.postgresql.org/about/licence/).
