## Why

postgast ships `walk()` and `Visitor` for AST traversal, but users have no interactive guide showing how to combine
these primitives for real-world SQL analysis tasks. A Marimo recipebook provides executable, self-documenting examples
that users can run, modify, and learn from — bridging the gap between API reference and practical application.

## What Changes

- Add a Marimo notebook (`recipes/ast_walker.py`) containing recipes for common AST walker patterns
- Each recipe demonstrates a self-contained SQL analysis task using `walk()`, `Visitor`, or both
- Recipes cover: table extraction, column collection, query complexity analysis, statement classification, schema
  dependency graphing, and subquery detection
- Add `marimo` as an optional dev/docs dependency
- The notebook is runnable standalone (`marimo run recipes/ast_walker.py`) or editable (`marimo edit`)

## Capabilities

### New Capabilities

- `ast-walker-recipebook`: Interactive Marimo notebook with executable recipes demonstrating walk()/Visitor patterns for
  SQL analysis — covers recipe structure, content requirements, and dependency setup

### Modified Capabilities

_(none — this adds documentation tooling, no library behavior changes)_

## Impact

- **New files**: `recipes/ast_walker.py` (Marimo notebook)
- **Dependencies**: `marimo` added as optional dependency (e.g., `[docs]` extra or dev dependency group)
- **Build**: No changes to library packaging — recipes are not distributed with the package
- **Existing code**: No modifications to `src/postgast/`; recipes import the public API only
- **Related**: Complements the planned `add-ast-helpers` change — recipes can showcase those helpers once implemented
