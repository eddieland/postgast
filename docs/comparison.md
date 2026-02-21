# Comparing postgast to Alternative Libraries

This document compares postgast against other Python libraries for parsing PostgreSQL SQL.

## Quick Comparison

| Capability | postgast | pglast | sqlglot | psqlparse | sqlparse |
| --- | --- | --- | --- | --- | --- |
| **Parser engine** | libpg_query (ctypes) | libpg_query (Cython) | Custom recursive-descent | libpg_query (Cython) | Custom tokenizer |
| **PG grammar fidelity** | 100% | 100% | High (not 100%) | 100% (old PG) | Low (non-validating) |
| **PostgreSQL version** | 17 | 17 (v7) | N/A | ~10 | N/A |
| **License** | BSD-2-Clause | **GPL-3.0+** | MIT | BSD-3-Clause | BSD-2-Clause |
| **Python versions** | 3.10+ | 3.9+ | 3.9+ | 3.5 | 3.8+ |
| **C toolchain required** | No (ctypes) | Yes (Cython) | No (pure Python) | Yes (Cython) | No (pure Python) |
| **Core deps** | protobuf | — | — | — | — |
| **Maintenance** | Active | Active | Very active | Dead (last release 2019) | Active |
| **Multi-dialect** | No (PG only) | No (PG only) | Yes (31+ dialects) | No (PG only) | Generic |

## Feature-by-Feature Breakdown

| Feature | postgast | pglast | sqlglot | psqlparse | sqlparse |
| --- | --- | --- | --- | --- | --- |
| **Parse SQL to AST** | Yes | Yes | Yes | Yes | Tokenize only |
| **Deparse AST to SQL** | Yes | Yes | Yes | No | No |
| **Normalize** | Yes (dedicated function) | Via `RawStream` | No | No | No |
| **Fingerprint** | Yes | Yes | No | No | No |
| **Split statements** | Yes (parser + scanner) | Yes (parser + scanner) | No | No | Yes |
| **Tokenize / scan** | Yes | Yes | Yes | No | Yes |
| **Pretty-print SQL** | No | Yes (`pgpp` CLI) | Yes | No | Yes |
| **Tree walking** | Yes (`walk()`) | Yes (visitors) | Yes (`.walk()`, `.find()`) | No | No |
| **Visitor pattern** | Yes (`Visitor` class) | Yes (`Visitor` class) | Yes (`.transform()`) | No | No |
| **AST helpers** | Yes (extract tables, columns, functions, DDL identities) | Manual via visitors | Yes (built-in finders) | Table extraction only | No |
| **AST modification + deparse** | Yes (modify protobuf, then deparse) | Yes (modify AST, then deparse) | Yes (transform + generate) | No | No |
| **PL/pgSQL parsing** | No | Yes | No | No | No |
| **SQL transpilation** | No | No | Yes (31+ dialects) | No | No |
| **SQL optimization** | No | No | Yes (predicate pushdown, etc.) | No | No |
| **CLI tool** | No | Yes (`pgpp`) | No | No | Yes (`sqlformat`) |

## Detailed Comparison with pglast

pglast is postgast's closest competitor — both wrap libpg_query and achieve 100% PostgreSQL grammar fidelity. The key
differences:

### Where postgast has an advantage

- **License**: BSD-2-Clause vs. GPL-3.0+. This is the primary motivation for postgast's existence. The GPL license makes
  pglast unusable in many commercial products and permissively-licensed open-source projects. Even the libpg_query
  maintainer [expressed surprise](https://github.com/lelit/pglast/issues/9) at pglast's GPL choice, since libpg_query
  itself is BSD-licensed.

- **No C toolchain needed**: postgast uses ctypes to call libpg_query directly — no Cython compilation step. This
  simplifies installation, cross-compilation, and CI environments. pglast requires Cython and a C compiler, or
  pre-built wheels.

- **Normalize (dedicated function)**: postgast exposes libpg_query's `pg_query_normalize` directly as a one-call
  function (replaces constants with `$1`, `$2`, … placeholders). pglast achieves normalization indirectly via
  `RawStream`, which is more verbose for this common operation.

- **Built-in AST helpers**: postgast ships convenience functions (`extract_tables`, `extract_columns`,
  `extract_functions`, `extract_function_identity`, `extract_trigger_identity`, `set_or_replace`, `ensure_or_replace`)
  that handle common extraction patterns out of the box. In pglast, these require writing custom visitors.

### Where pglast has an advantage

- **Pretty-printing**: pglast includes `IndentedStream` and `RawStream` for SQL pretty-printing with configurable
  indentation and formatting. It also ships a `pgpp` CLI tool. postgast does not have a pretty-printer — `deparse()`
  returns canonicalized (but not formatted) SQL.

- **PL/pgSQL parsing**: pglast can parse PL/pgSQL function bodies into an AST. postgast only parses SQL-level
  statements.

- **Typed AST classes**: pglast auto-generates concrete Python classes (`pglast.ast.*`) for every PostgreSQL node type,
  with mutable attribute access and self-serialization. postgast uses raw protobuf `Message` objects, which are
  functional but less ergonomic for complex AST surgery.

- **Richer visitor semantics**: pglast's `Visitor` supports return values that control traversal — `Delete` (remove
  node), `Skip` (don't descend), `Add` (insert siblings), or return a new node to replace the current one. It also
  provides `Ancestor` tracking for full ancestry chains. postgast's `Visitor` uses a simpler override-and-recurse model.

- **Maturity and ecosystem**: pglast has been maintained since 2017, has ~41K weekly PyPI downloads, 99% test coverage,
  and comprehensive documentation on ReadTheDocs. postgast is newer with a smaller user base.

- **CLI tooling**: pglast's `pgpp` command-line tool can prettify SQL files directly. postgast is library-only.

### Feature parity

Both libraries offer: parsing, deparsing, fingerprinting, statement splitting (parser and scanner modes), tokenization /
scanning, tree walking/visitor patterns, and AST modification with round-trip deparsing.

## Detailed Comparison with sqlglot

sqlglot occupies a different niche — it is a multi-dialect SQL toolkit, not a PostgreSQL-specific parser.

### When to choose sqlglot

- You need to **transpile** between SQL dialects (e.g., Spark to PostgreSQL).
- You need to parse SQL from **multiple database engines**, not just PostgreSQL.
- You need SQL **optimization** passes (predicate pushdown, constant folding).
- You want **zero native dependencies** — sqlglot is pure Python with no C library.

### When to choose postgast

- You need **100% PostgreSQL grammar fidelity**. sqlglot's hand-written parser covers most PostgreSQL syntax but cannot
  guarantee it handles every construct the real PostgreSQL parser accepts. postgast uses PostgreSQL's actual parser, so
  if PostgreSQL can parse it, so can postgast.
- You need **normalize** or **fingerprint** functionality.
- You are building PostgreSQL-specific tooling (migration tools, query analyzers, linters) where correctness against the
  PostgreSQL grammar is non-negotiable.

## Other Libraries

| Library | Notes |
| --- | --- |
| **psqlparse** | Dead since 2019. Thin Cython wrapper around an old libpg_query — parse-only, no deparse, no fingerprint. Superseded by pglast and postgast. |
| **pg_query** (PyPI) | Deprecated — this was pglast's original name before being renamed. Not a separate project. |
| **sqlparse** | Non-validating tokenizer/formatter. Extremely popular (~14.6M weekly downloads) because Django depends on it, but it does not produce a semantic AST. Suitable for formatting and splitting, not for analysis or transformation. |
| **mo-sql-parsing** | Niche pure-Python parser (uses `mo-parsing`). Converts SQL to JSON structures. Partial PostgreSQL support. MPL-2.0 licensed. Low adoption. |

## Summary

postgast fills a specific gap in the ecosystem: **a permissively-licensed, actively maintained Python library with 100%
PostgreSQL parsing fidelity**. Before postgast, users had to choose between pglast (100% fidelity, GPL) and sqlglot
(permissive license, imperfect PG fidelity). postgast offers both.

The trade-off is that postgast does not yet have pglast's pretty-printer or PL/pgSQL support, and it does not attempt
sqlglot's multi-dialect transpilation. It focuses on being a correct, minimal, and permissively-licensed PostgreSQL
parser.
