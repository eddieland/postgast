## Tasks

### 1. Add `walk_typed()` function

Add a `walk_typed()` generator to `src/postgast/walk.py` that delegates to the existing `walk()` and wraps results.

- Accepts `AstNode`, yields `tuple[str, AstNode]`
- Delegates to `walk(node._pb)` internally and wraps each result with `wrap()`
- Preserves the same traversal order and `Node` unwrapping behavior as `walk()`

**Files:** `src/postgast/walk.py` (modified)

**Acceptance criteria:**

- `walk_typed(wrapped_tree)` yields the same nodes in the same order as `walk(tree)`, but as `AstNode` instances
- No `Node` oneof wrappers appear in results
- Existing `walk()` is unchanged

### 2. Add `TypedVisitor` class

Add a `TypedVisitor` base class to `src/postgast/walk.py` alongside the existing `Visitor`.

- `visit(node: AstNode)` dispatches to `visit_<ClassName>()` or `generic_visit()`
- `generic_visit(node: AstNode)` recurses into child nodes
- Handler methods receive typed wrappers (e.g., `visit_SelectStmt(self, node: SelectStmt)`)

**Files:** `src/postgast/walk.py` (modified)

**Acceptance criteria:**

- `TypedVisitor` dispatches correctly to type-specific handlers
- Falls back to `generic_visit` for unhandled types
- Existing `Visitor` is unchanged

### 3. Update `deparse()` to accept wrappers

Modify `deparse()` to detect `AstNode` wrappers (via `_pb` attribute) and extract the underlying protobuf before
processing.

**Files:** `src/postgast/deparse.py` (modified)

**Acceptance criteria:**

- `deparse(parse("SELECT 1"))` works (existing behavior)
- `deparse(wrap(parse("SELECT 1")))` works (new behavior)
- Type signature accepts both `ParseResult` and wrapper types

### 4. Update `__init__.py` re-exports

Export `walk_typed` and `TypedVisitor` from the `postgast` package.

**Files:** `src/postgast/__init__.py` (modified)

**Acceptance criteria:**

- `from postgast import walk_typed, TypedVisitor` works
- `__all__` is updated

### 5. Add generation freshness CI check

Add Makefile targets for node generation and verification.

- `make generate-nodes` — runs `uv run python scripts/generate_nodes.py`
- `make check-nodes` — regenerates to a temp file and diffs against committed `nodes.py`, fails if different

**Files:** `Makefile` (modified)

**Acceptance criteria:**

- `make generate-nodes` runs successfully
- `make check-nodes` passes when `nodes.py` is up to date
- `make check-nodes` fails with a clear message when `nodes.py` is stale

### 6. Write tests

Add tests covering `walk_typed()`, `TypedVisitor`, and deparse wrapper support.

**Files:** `tests/postgast/test_walk.py` (modified), `tests/postgast/test_deparse.py` (modified or new test added)

**Acceptance criteria:**

- `walk_typed` returns `AstNode` instances in correct order
- `TypedVisitor` dispatches to typed handlers and collects results
- `deparse(wrap(parse(sql)))` roundtrips correctly for SELECT, INSERT, CREATE TABLE
- All existing tests still pass

### 7. Lint and test pass

Ensure the full project passes all checks.

**Acceptance criteria:**

- `make lint` passes (ruff + basedpyright)
- `make test` passes (all existing + new tests)
- No regressions in existing functionality
