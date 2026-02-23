## Why

The `typed-ast-wrappers` change introduces typed Python wrapper classes for the protobuf AST, but deliberately defers
integration with the rest of postgast's API surface. Without this follow-up, users must manually bridge between the
typed wrappers and existing utilities — calling `deparse(node._pb)` instead of `deparse(node)`, and using the untyped
`walk()`/`Visitor` that yield raw `Message` objects even when working with typed wrappers.

## What Changes

- Add `walk_typed()` and `TypedVisitor` that accept/yield typed `AstNode` wrappers instead of raw protobuf `Message`
  objects
- Update `deparse()` to accept typed wrappers directly (extracting `._pb` internally)
- Add a CI freshness check ensuring generated `nodes.py` stays in sync with the protobuf schema

## Capabilities

### New Capabilities

- `typed-tree-walking`: Typed alternatives to `walk()` and `Visitor` that work with `AstNode` wrappers, providing IDE
  autocomplete and type safety in visitor handlers

### Modified Capabilities

- `ast-navigation`: `deparse()` accepts both raw `ParseResult` and wrapped `nodes.ParseResult`

## Impact

- `src/postgast/walk.py` — Add `walk_typed()` and `TypedVisitor` alongside existing untyped versions
- `src/postgast/deparse.py` — Accept wrapped types in `deparse()`
- `src/postgast/__init__.py` — Re-export `walk_typed`, `TypedVisitor`
- `tests/postgast/test_walk.py` — New tests for typed walking/visiting
- `Makefile` — Add `make generate-nodes` and `make check-nodes` targets
