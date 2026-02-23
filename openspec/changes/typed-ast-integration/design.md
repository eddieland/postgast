## Context

This change builds on `typed-ast-wrappers`, which provides generated wrapper classes in `src/postgast/nodes.py` with a
`wrap()` function and `AstNode` base class. The existing `walk()` generator and `Visitor` base class in
`src/postgast/walk.py` operate on raw protobuf `Message` objects. The goal is to add typed alternatives alongside them.

## Goals / Non-Goals

**Goals:**

- Add `walk_typed()` and `TypedVisitor` as typed alternatives to `walk()` and `Visitor`
- Accept typed wrappers in `deparse()`
- Add CI verification that `nodes.py` stays in sync with the protobuf schema

**Non-Goals:**

- Replacing `walk()` or `Visitor` (they remain unchanged)
- Making helpers use typed wrappers internally (separate future change)

## Design

### Decision 1: `walk_typed()` delegates to `walk()` + `wrap()`

**Decision:** `walk_typed()` calls the existing `walk()` internally and wraps each yielded message with `wrap()`.

```python
def walk_typed(node: AstNode) -> Generator[tuple[str, AstNode], None, None]:
    for field_name, message in walk(node._pb):
        yield field_name, wrap(message)
```

**Rationale:** Avoids duplicating the traversal logic. `walk()` already handles `Node` oneof unwrapping, field
discovery, and recursion. Wrapping the output is a thin layer.

**Alternative considered:** Reimplementing traversal over wrapper objects. Rejected because wrapper properties create
new lists on each access, making recursive traversal less efficient than operating on the underlying protobuf messages.

### Decision 2: `TypedVisitor` mirrors `Visitor` with wrapper dispatch

**Decision:** `TypedVisitor` follows the same structure as `Visitor` — `visit()` resolves the type name and calls
`visit_<ClassName>()` or `generic_visit()`. The difference is that it uses the wrapper class name (from
`type(node).__name__`) instead of the protobuf descriptor name.

```python
class TypedVisitor:
    def visit(self, node: AstNode) -> None:
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        visitor(node)

    def generic_visit(self, node: AstNode) -> None:
        for _field_name, child in walk_children_typed(node):
            self.visit(child)
```

**Rationale:** Maintains API parity with `Visitor` so users can migrate by changing the base class and adding type
annotations. The wrapper class names match the protobuf descriptor names, so handler method names are identical.

### Decision 3: `deparse()` detects wrappers via `_pb` attribute

**Decision:** `deparse()` checks for a `_pb` attribute on the input. If present, it extracts the underlying protobuf
message before passing to the C library.

```python
def deparse(tree: ParseResult | AstNode) -> str:
    if hasattr(tree, "_pb"):
        tree = tree._pb
    # existing deparse logic
```

**Rationale:** Minimal change, no new dependencies. The duck-typing approach avoids importing from `nodes` module,
preventing circular imports.

### Decision 4: CI freshness check via Makefile

**Decision:** Add `make generate-nodes` (runs the generator) and `make check-nodes` (regenerates to a temp file and
diffs against committed version, failing if different).

**Rationale:** Catches cases where `pg_query_pb2.py` is updated but `nodes.py` isn't regenerated. Simple diff-based
check requires no additional tooling.

## Risks / Trade-offs

**Double wrapping cost** — `walk_typed()` wraps every yielded node, adding allocation overhead for large trees. This is
acceptable because typed walking is opt-in; users who need raw performance use `walk()`.

**Visitor method signatures** — `TypedVisitor` handler return types match the wrapper class name, so `visit_SelectStmt`
works the same for both `Visitor` and `TypedVisitor`. Migration is just a base class change + type annotations.
