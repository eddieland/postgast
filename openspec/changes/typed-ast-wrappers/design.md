## Context

postgast parses SQL into protobuf `ParseResult` messages defined in `pg_query_pb2.py` (generated from libpg_query's
`.proto` schema). The protobuf layer has 277 message types and uses a `Node` oneof wrapper — a single message with ~230
optional fields, each holding one concrete node type. Every polymorphic field (e.g., `SelectStmt.where_clause`,
`InsertStmt.select_stmt`) is typed as `Node`, hiding the actual concrete type.

Current user code to access a WHERE clause's column reference looks like:

```python
tree = postgast.parse("SELECT * FROM t WHERE x = 1")
stmt = tree.stmts[0].stmt  # Node wrapper
select = stmt.select_stmt  # SelectStmt (must know the field name)
where = select.where_clause  # Node wrapper again
which = where.WhichOneof("node")  # "a_expr"
a_expr = getattr(where, which)  # A_Expr
# ... more unwrapping for lexpr/rexpr
```

This is verbose, untyped, and hostile to IDE autocomplete. The goal is a wrapper layer where the same operation becomes:

```python
tree = postgast.parse("SELECT * FROM t WHERE x = 1")
stmt = tree.stmts[0].stmt  # SelectStmt (unwrapped)
where = stmt.where_clause  # A_Expr (unwrapped)
col = where.lexpr  # ColumnRef (unwrapped)
```

## Goals / Non-Goals

**Goals:**

- Provide typed Python wrappers for all protobuf AST node types
- Automatic, transparent unwrapping of `Node` oneof wrappers
- Convert protobuf repeated fields to standard Python sequences
- Support `match`/`case` structural pattern matching (Python 3.10+)
- Generate wrapper code from the protobuf schema (not hand-maintained)
- Zero runtime cost for users who don't use wrappers (opt-in at first, default later)
- Full type checker support (basedpyright, mypy)

**Non-Goals:**

- Mutable AST modification through wrappers (read-only wrappers first; mutation is a future change)
- Replacing protobuf as the parse result format (wrappers are a layer on top)
- Wrapping every protobuf enum type (enums are already usable as-is)
- Building a SQL-construction DSL (this is about reading parse trees, not building them)

## Design

### Architecture: Thin Wrappers Over Protobuf

Each wrapper class holds a reference to the underlying protobuf message and provides typed property access. This avoids
copying data and keeps memory overhead minimal.

```python
class AstNode:
    """Base class for all typed AST wrappers."""

    __slots__ = ("_pb",)

    def __init__(self, pb: Message) -> None:
        self._pb = pb

    def __repr__(self) -> str:
        return f"{type(self).__name__}(...)"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AstNode):
            return self._pb == other._pb
        return NotImplemented

    def __hash__(self) -> int:
        return id(self._pb)
```

Each concrete node class is a subclass:

```python
class SelectStmt(AstNode):
    __slots__ = ()
    __match_args__ = ("target_list", "from_clause", "where_clause")

    @property
    def target_list(self) -> list[AstNode]:
        return [wrap(n) for n in self._pb.target_list]

    @property
    def from_clause(self) -> list[AstNode]:
        return [wrap(n) for n in self._pb.from_clause]

    @property
    def where_clause(self) -> AstNode | None:
        return wrap_optional(self._pb.where_clause)

    @property
    def group_clause(self) -> list[AstNode]:
        return [wrap(n) for n in self._pb.group_clause]

    # ... other fields
```

### Decision 1: Generated code vs. runtime metaprogramming

**Decision:** Generate wrapper classes as a Python source file (`src/postgast/nodes.py`) from the protobuf descriptor at
development time.

**Rationale:**

- Static source enables type checkers (basedpyright) to validate all attribute access
- IDE autocomplete works out of the box (no runtime `__getattr__` tricks)
- Generated code can include `__match_args__` for pattern matching
- Easier to review, debug, and understand than metaclass magic
- Follows the same pattern as `pg_query_pb2.py` / `pg_query_pb2.pyi` (generated, checked in)

**Alternative considered:** Runtime wrapper creation via metaclass or `__init_subclass__`. Rejected because it defeats
the purpose of typed access — type checkers can't see attributes defined at runtime.

**Alternative considered:** Hand-written wrappers for common types only. Rejected because it creates an inconsistent API
(some nodes wrapped, others not) and doesn't scale with protobuf schema updates.

### Decision 2: Wrapper dispatch — `wrap()` function with registry

**Decision:** A `wrap(node: Message) -> AstNode` function uses a dictionary mapping protobuf descriptor names to wrapper
classes. For `Node` oneof wrappers, it first calls `WhichOneof("node")` to get the concrete field, then wraps the inner
message.

```python
_REGISTRY: dict[str, type[AstNode]] = {
    "SelectStmt": SelectStmt,
    "InsertStmt": InsertStmt,
    # ... all 277 types
}


def wrap(pb: Message) -> AstNode:
    """Wrap a protobuf message in its typed AST wrapper."""
    # Unwrap Node oneof if needed
    desc = type(pb).DESCRIPTOR
    if len(desc.oneofs) == 1 and desc.oneofs[0].name == "node":
        which = pb.WhichOneof("node")
        if which is not None:
            pb = getattr(pb, which)
    cls = _REGISTRY.get(type(pb).DESCRIPTOR.name, AstNode)
    return cls(pb)
```

**Rationale:** Simple, fast O(1) lookup. The registry is populated by the generated code. Unrecognized types fall back
to the base `AstNode` class for forward compatibility.

### Decision 3: Property return types — concrete where possible, union otherwise

**Decision:** Fields where the protobuf schema specifies a concrete type (e.g., `InsertStmt.relation: RangeVar`) return
the concrete wrapper type. Fields typed as `Node` (the oneof wrapper) return `AstNode` — the base wrapper type.

```python
class InsertStmt(AstNode):
    @property
    def relation(self) -> RangeVar:  # Concrete — protobuf field is RangeVar
        return RangeVar(self._pb.relation)

    @property
    def select_stmt(self) -> AstNode | None:  # Polymorphic — protobuf field is Node
        return wrap_optional(self._pb.select_stmt)
```

**Rationale:** This gives maximum type safety where the schema allows it. For polymorphic fields, users can narrow with
`isinstance` checks or `match`/`case`, which is idiomatic Python and compatible with type narrowing in type checkers.

**Alternative considered:** Union types like `SelectStmt | InsertStmt | ...` for polymorphic fields. Rejected — the
union of 230+ types is impractical and provides no benefit over the base class approach.

### Decision 4: Repeated fields — return `list`, not `Sequence`

**Decision:** Properties for repeated protobuf fields return `list[AstNode]` (or `list[ConcreteType]`), materializing
the wrapper list eagerly.

**Rationale:** Lists are the most Pythonic collection type. Lazy wrappers add complexity (custom sequence classes) for
minimal benefit — parse trees are typically small. Returning `list` also simplifies pattern matching.

**Trade-off:** Each property access creates a new list. We can add `@functools.cached_property` if profiling shows this
matters, but protobuf messages are not hashable by default, so we start simple.

### Decision 5: Opt-in initially, default later

**Decision:** Initially provide `wrap()` as an explicit function. Users call `postgast.wrap(tree)` to get typed
wrappers. The existing `parse()` continues to return raw `ParseResult`. In a future release, `parse()` can return
wrapped types by default.

```python
# Phase 1 (this change):
tree = postgast.parse("SELECT 1")  # Returns ParseResult (protobuf)
typed = postgast.wrap(tree)  # Returns typed ParseResult wrapper

# Phase 2 (future change):
tree = postgast.parse("SELECT 1")  # Returns typed wrapper by default
raw = postgast.parse_raw("SELECT 1")  # Returns raw protobuf if needed
```

**Rationale:** Non-breaking introduction. Existing code continues to work. Users migrate at their own pace. The
`deparse()` function accepts both raw protobuf and wrappers (by extracting `._pb` when given a wrapper).

### Decision 6: Code generation approach

**Decision:** A generation script (`scripts/generate_nodes.py`) introspects the protobuf descriptor at import time and
emits `src/postgast/nodes.py`. It runs with `uv run python scripts/generate_nodes.py` and the output is checked into
version control.

The script:

1. Imports `pg_query_pb2` and iterates over `DESCRIPTOR.message_types_by_name`
1. For each message type, inspects fields via the `FieldDescriptor`
1. Classifies each field: scalar (passthrough), message (wrap), repeated message (wrap list), Node oneof (unwrap+wrap)
1. Emits a class with `__slots__`, `__match_args__`, and typed `@property` accessors
1. Emits the `_REGISTRY` dict
1. Emits `wrap()`, `wrap_optional()`, and `wrap_list()` helper functions

**Rationale:** Using protobuf's own descriptor ensures the generated code stays in sync with the `.proto` schema. The
script is simple Python (string templating), not a complex AST manipulation framework.

### Decision 7: Pattern matching support

**Decision:** Each wrapper class defines `__match_args__` with its most useful fields, enabling:

```python
match stmt:
    case SelectStmt(target_list=targets, where_clause=where):
        ...
    case InsertStmt(relation=rel):
        ...
```

**Rationale:** Python 3.10+ pattern matching is the primary reason users want typed wrappers. The project already
targets Python 3.10+.

For `__match_args__`, the generator includes all non-location, non-internal fields. Users can match on any field by
name.

### Deferred: Integration with walk/Visitor, deparse, CI check

The following are deferred to a follow-up change (`typed-ast-integration`):

- `walk_typed()` and `TypedVisitor` — typed alternatives to existing walk/Visitor
- `deparse()` accepting wrapped types — users can use `deparse(node._pb)` as a workaround
- CI freshness check (`make check-nodes`) — manual responsibility to re-run generator for now

## Risks / Trade-offs

**Generated file size** — With 277 message types averaging ~15 fields each, `nodes.py` will be ~5,000–8,000 lines. This
is comparable to `pg_query_pb2.py` (~7,000 lines) and is acceptable for generated code.

**Property overhead** — Each field access creates wrapper objects. For hot loops over large trees, this adds allocation
overhead. Mitigated by keeping the base `AstNode` lightweight (`__slots__` with single `_pb` field). If profiling shows
issues, we can add caching or a "fast path" that operates on raw protobuf.

**Keeping generated code in sync** — When `libpg_query` updates its `.proto` schema (PostgreSQL version bumps), the
generation script must be re-run. Mitigated by adding a CI check that verifies `nodes.py` matches the current protobuf
descriptor, similar to how protobuf stubs are verified.

**Deparse compatibility** — `deparse()` currently accepts `ParseResult` (protobuf). Users can pass `node._pb` to
`deparse()` as a workaround. Native wrapper support is deferred to `typed-ast-integration`.
