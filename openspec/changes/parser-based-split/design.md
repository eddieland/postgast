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
- Preserve full backward compatibility (default behavior unchanged)

**Non-Goals:**

- Changing the default split method — scanner remains the default
- Adding a separate top-level `split_with_parser()` function
- Exposing parser options (e.g., `PgQueryParseMode`) for the split call — libpg_query's split functions don't accept
  parser options

## Decisions

### 1. Single function with `method` parameter vs. separate functions

**Decision:** Add a `method` parameter to the existing `split()` function.

**Alternatives considered:**

- *Separate `split_with_parser()` function* — adds API surface for a single flag toggle; the two functions would share
  identical signatures and return types, making them redundant.
- *Replace scanner with parser entirely* — would break callers relying on the scanner's tolerance of invalid SQL.

**Rationale:** A parameter keeps the API surface small and mirrors how libpg_query names the two variants (same prefix,
different suffix). Users who don't care about the method never see the parameter.

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

- **Parser method rejects invalid SQL** → Expected behavior, documented. Users needing tolerance for broken SQL should
  use the default `"scanner"` method.
- **Minimal test coverage difference** — Both methods share the same result struct and slicing logic; the risk is low.
  Tests will cover parser-specific edge cases (e.g., `CREATE RULE` with inner semicolons) to confirm improved accuracy.
