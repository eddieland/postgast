## Why

Working with postgast's parse tree today requires dealing with raw protobuf `Message` objects and the `Node` oneof
wrapper. This is painful in several ways:

1. **No type safety** — Fields like `SelectStmt.where_clause` are typed as `Node` (the oneof wrapper), not as the
   concrete type they contain. Code must call `node.WhichOneof("node")` + `getattr(node, which)` to unwrap, which is
   verbose and untyped.

1. **Protobuf API friction** — Users must understand protobuf idioms (`HasField`, `WhichOneof`, `ListFields`,
   `RepeatedCompositeFieldContainer`) rather than using idiomatic Python (attribute access, iteration, pattern
   matching).

1. **No IDE support** — Because the walk/visitor APIs accept and yield `Message`, IDEs cannot autocomplete field names
   or catch attribute errors. The `visit_RangeVar` handler receives `Message`, not `RangeVar`.

1. **Boilerplate in helpers** — Every helper function in `helpers.py` manually unwraps `Node` wrappers with the same
   `WhichOneof` / `getattr` pattern. The `extract_columns` function is 12 lines of unwrapping for what should be
   `col_ref.fields[0].sval`.

Libraries like pglast provide a Pythonic AST layer over the same underlying PostgreSQL parse tree. postgast should offer
a similar experience without forcing users to learn protobuf internals.

## What Changes

Add a typed AST wrapper layer that:

- Provides Python classes for each protobuf node type with properly typed attributes
- Automatically unwraps `Node` oneof wrappers so users never see them
- Converts `RepeatedCompositeFieldContainer` to standard Python lists
- Supports `match`/`case` pattern matching (Python 3.10+)
- Integrates with the existing `walk`, `Visitor`, and helper APIs
- Is generated from the protobuf schema (not hand-written for 277 message types)

## Capabilities

### New Capabilities

- `typed-ast-wrappers`: Typed Python wrapper classes for all 277 protobuf AST node types, with automatic `Node` oneof
  unwrapping, Pythonic attribute access, and structural pattern matching support

### Modified Capabilities

- `parse`: Returns typed wrapper instead of raw protobuf (or provides an opt-in wrapper function)
- `tree-walking`: Walk and Visitor yield/accept typed wrappers instead of raw `Message` objects
- `ast-helpers`: Simplified implementations using typed wrappers internally

## Impact

- `src/postgast/nodes.py` (new) — Generated typed wrapper classes
- `src/postgast/parse.py` — Potentially updated to return wrapped types
- `src/postgast/walk.py` — Updated to yield typed wrappers
- `src/postgast/helpers.py` — Simplified using typed field access
- `src/postgast/__init__.py` — New re-exports
- `tests/postgast/test_nodes.py` (new) — Tests for wrapper classes
- `scripts/generate_nodes.py` or `codegen/` (new) — Code generation script
