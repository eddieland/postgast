## Context

postgast can parse SQL into a protobuf AST and deparse it back via libpg_query's C deparser, but the output is always a
single canonical line with no formatting. The library already has a `Visitor` base class and `walk()` generator for AST
traversal, plus `deparse()` as a correctness oracle. A pretty-printer can build on these foundations — walk the AST with
a visitor, emit formatted SQL, and validate output by round-tripping through `parse()` + `deparse()`.

The protobuf AST is deeply nested: `ParseResult` → `RawStmt` → statement nodes (e.g. `SelectStmt`) → expression nodes
(`A_Expr`, `FuncCall`, `ColumnRef`, `SubLink`, etc.). Each statement type has different clause fields (e.g.
`SelectStmt.target_list`, `SelectStmt.from_clause`, `SelectStmt.where_clause`). The formatter must handle each clause
type explicitly — generic tree-walking alone cannot produce readable SQL because formatting rules are clause-specific.

## Goals / Non-Goals

**Goals:**

- Produce deterministic, readable SQL from any `ParseResult` or SQL string
- Handle core DML (SELECT, INSERT, UPDATE, DELETE) and common DDL (CREATE TABLE, ALTER TABLE, DROP, CREATE INDEX, CREATE
  VIEW) with clause-level formatting
- Zero configuration — one canonical format, no options in v1
- Pure Python — no C dependency beyond what `parse()` already requires
- Correct output — formatted SQL must parse to a semantically equivalent AST

**Non-Goals:**

- Comment preservation (comments are discarded during parsing — this is a libpg_query limitation, not something we can
  work around). **Future path**: `scan()` captures `C_COMMENT` and `SQL_COMMENT` tokens with byte positions, so a
  post-processing layer could reattach comments to the formatted output by associating each comment token with the
  nearest clause or expression. This would layer on top of the AST visitor without changing it.
- Configurable style (line width, indent size, keyword casing) — deliberate omission for v1
- Formatting of PL/pgSQL or procedural blocks (function bodies are opaque strings in the AST)
- Performance optimization — correctness and readability first; this is not a hot path

## Decisions

### 1. Visitor-based emitter, not a doc-algebra pretty-printer

**Decision**: Build the formatter as a `Visitor` subclass that emits SQL strings directly by dispatching on AST node
types, rather than using an intermediate document algebra (like Wadler-Lindig or the `prettyprinter` library).

**Rationale**: SQL formatting is clause-driven, not expression-driven. Most formatting decisions are at the clause level
(WHERE goes on a new line, SELECT items get one-per-line) rather than requiring optimal line-breaking of deeply nested
expressions. A visitor maps naturally to "for each clause, emit keyword + indented body." A doc-algebra adds complexity
without meaningful benefit for SQL's relatively flat clause structure.

**Alternative considered**: Wadler-Lindig pretty-printer with `group`/`nest`/`break` combinators. This excels at
flexible line-breaking for languages with deep nesting (Haskell, OCaml), but SQL's formatting conventions are more rigid
(clause-per-line is always desired, not a "break if it doesn't fit" choice). The added abstraction layer would make
clause-specific rules harder to express.

### 2. Build on the existing Visitor class from walk.py

**Decision**: Subclass `postgast.walk.Visitor` and implement `visit_<TypeName>` methods for each statement and
expression type that needs formatting.

**Rationale**: The `Visitor` class already handles Node oneof unwrapping, dispatch by type name, and recursive traversal
via `generic_visit`. Reusing it keeps the formatter consistent with the rest of the codebase and avoids reimplementing
dispatch logic.

**Alternative considered**: A standalone dispatch function using `match`/`case` or a dict-based dispatcher. This would
work but duplicates the unwrapping and dispatch pattern that `Visitor` already provides.

### 3. Accumulate output in a list of strings, join at the end

**Decision**: The visitor accumulates formatted fragments into a `list[str]`, then joins them at the end. An internal
`_emit()` method appends text, and `_newline()` / `_indent()` / `_dedent()` manage indentation state.

**Rationale**: String concatenation in a loop is O(n²) in the worst case. List append + join is O(n) and is the standard
Python pattern for building strings incrementally. The indent/dedent helpers keep formatting logic readable without
passing indentation depth through every method.

### 4. Accept both SQL strings and ParseResult objects

**Decision**: `format_sql()` accepts `str | ParseResult`. If given a string, it calls `parse()` internally.

**Rationale**: Most users have a SQL string and want it formatted. Requiring them to call `parse()` first adds friction.
Accepting `ParseResult` too supports users who already have a parsed tree (e.g., after AST manipulation).

### 5. Fallback to deparse() for unhandled node types

**Decision**: When the formatter encounters a statement or expression type it doesn't have a specific `visit_*` handler
for, it falls back to `deparse()` to produce unformatted but correct SQL for that subtree.

**Rationale**: PostgreSQL has 100+ statement types. Implementing formatters for all of them in v1 is impractical. The
fallback ensures `format_sql()` never crashes on valid SQL — it just produces unformatted output for uncommon statement
types. This lets us ship a useful formatter quickly and expand coverage incrementally.

**Trade-off**: Fallback output is single-line and uses libpg_query's casing conventions, which may look inconsistent
next to formatted output. This is acceptable for v1 — uncommon statements in a multi-statement input will just look
"plain" rather than broken.

### 6. Validate correctness via parse-deparse round-trip in tests

**Decision**: Tests verify that `parse(deparse(parse(format_sql(sql))))` produces the same canonical form as
`parse(deparse(parse(sql)))` — i.e., formatting doesn't change semantics.

**Rationale**: `deparse()` produces a canonical form. If the formatted SQL parses to the same canonical form as the
original, the formatter preserved semantics. This is a strong, automated correctness check that doesn't require
hand-verifying every output.

## Risks / Trade-offs

**AST may lack information needed for ideal formatting** → Accept imperfect output for edge cases. For example,
`A_Const` doesn't preserve the original literal format (hex vs. decimal), so the formatter emits whatever the protobuf
stores. The output is correct, just potentially different from the original.

**Large surface area of PostgreSQL syntax** → The deparse fallback (Decision 5) ensures correctness for unhandled types.
Prioritize SELECT/INSERT/UPDATE/DELETE and common DDL; expand coverage based on user feedback.

**No comment preservation** → This is a fundamental limitation of the parse-tree approach (libpg_query discards
comments). Document this clearly. Users who need comment-preserving formatting need a token-level formatter, which is a
different tool.

**Single format may not satisfy all users** → This is intentional for v1 ("Black for SQL"). Configuration can be added
later as a backward-compatible enhancement if demand warrants it.
