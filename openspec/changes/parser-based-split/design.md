## Context

The `split()` function currently calls `pg_query_split_with_scanner` unconditionally. libpg_query ships a second
splitter, `pg_query_split_with_parser`, that uses the full PostgreSQL parser for improved accuracy. Both functions share
the same C signature (`const char* → PgQuerySplitResult`) and the same result struct, so the integration surface is
minimal.

The scanner-based splitter tolerates malformed SQL (useful for linters, editors), while the parser-based splitter
handles additional token edge cases that the scanner misses (useful for migration tools, query pipelines with
known-valid SQL).

## Goals / Non-Goals

**Goals:**

- Expose `pg_query_split_with_parser` through the existing `split()` public API
- Let callers choose between scanner and parser methods via a `method` parameter
- Default to the parser method, as recommended by libpg_query upstream

**Non-Goals:**

- Adding a separate top-level `split_with_parser()` function
- Exposing parser options (e.g., `PgQueryParseMode`) for the split call — libpg_query's split functions don't accept
  parser options

## Decisions

### 1. Single function with `method` parameter vs. separate functions

**Decision:** Add a `method` parameter to the existing `split()` function.

**Alternatives considered:**

- *Separate `split_with_parser()` function* — adds API surface for a single flag toggle; the two functions would share
  identical signatures and return types, making them redundant.
- *Replace scanner with parser entirely* — would remove the scanner fallback for invalid SQL.

**Rationale:** A parameter keeps the API surface small and mirrors how libpg_query names the two variants (same prefix,
different suffix). Defaulting to `"parser"` follows the upstream recommendation; callers needing scanner tolerance can
opt in with `method="scanner"`.

### 2. Parameter type: Literal string union vs. enum

**Decision:** Use `Literal["scanner", "parser"]` for the `method` parameter type.

**Alternatives considered:**

- *Enum class* — heavier API for just two values; requires an import for callers.
- *Boolean `use_parser`* — less readable, harder to extend if a third method ever appears.

**Rationale:** Literal strings are lightweight, self-documenting, and work well with type checkers. They match the
naming used in the libpg_query header (`split_with_scanner`, `split_with_parser`).

### 3. Dispatch implementation

**Decision:** Map the method string to the corresponding `lib.pg_query_split_with_*` function at the top of `split()`,
then call the selected function. Raise `ValueError` for unrecognized method values.

Both C functions return the same `PgQuerySplitResult` struct and are freed with the same `pg_query_free_split_result`,
so all existing result-handling and memory-cleanup code is reused without duplication.

## Risks / Trade-offs

- **Default change rejects invalid SQL that scanner tolerated** → Acceptable pre-1.0 breaking change. Users needing
  tolerance for broken SQL can pass `method="scanner"`.
- **Minimal test coverage difference** — Both methods share the same result struct and slicing logic; the risk is low.
  Tests will cover parser-specific edge cases (e.g., `CREATE RULE` with inner semicolons) to confirm improved accuracy.
