"""AST Walker Recipebook — interactive examples for postgast tree traversal."""

import marimo

__generated_with = "0.19.11"
app = marimo.App()


@app.cell
def _(mo):
    mo.md("""
    # AST Walker Recipebook

    Interactive recipes demonstrating how to traverse and analyze PostgreSQL
    parse trees using **postgast**'s `walk()` generator and `Visitor` pattern.

    Each recipe is self-contained: it defines a SQL input, runs analysis code,
    and displays the results.

    **How to use this notebook:**

    - `marimo run recipes/ast_walker.py` — read-only app mode
    - `marimo edit recipes/ast_walker.py` — interactive editing mode (tweak SQL, see results update)
    """)
    return


@app.cell
def _():
    import marimo as mo

    from postgast import Visitor, parse, walk

    return Visitor, mo, parse, walk


@app.cell
def _(Visitor, mo, parse):
    # --- Recipe: Extract table names ---
    _sql = "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id JOIN products p ON o.product_id = p.id"
    _tree = parse(_sql)

    class _TableCollector(Visitor):
        def __init__(self):
            self.tables = []

        def visit_RangeVar(self, node):
            self.tables.append(node.relname)

    _collector = _TableCollector()
    _collector.visit(_tree)

    mo.md(
        f"""
        ## Recipe 1: Extract Table Names

        Uses a `Visitor` subclass with `visit_RangeVar` to collect every table
        referenced in a query.

        **SQL:**
        ```sql
        {_sql}
        ```

        **Tables found:** {", ".join(f"`{t}`" for t in _collector.tables)}
        """
    )
    return


@app.cell
def _(mo, parse, walk):
    # --- Recipe: Collect column references ---
    _sql = "SELECT u.name, u.email, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'active'"
    _tree = parse(_sql)

    _columns = []
    for _field_name, _msg in walk(_tree):
        if type(_msg).__name__ == "ColumnRef":
            _parts = [f.string.sval for f in _msg.fields if f.HasField("string")]
            if _parts:
                _columns.append(".".join(_parts))

    mo.md(
        f"""
        ## Recipe 2: Collect Column References

        Uses `walk()` to iterate over all nodes, filtering for `ColumnRef` types
        and extracting column names from the `fields` repeated field.

        **SQL:**
        ```sql
        {_sql}
        ```

        **Columns found:** {", ".join(f"`{c}`" for c in _columns)}
        """
    )
    return


@app.cell
def _(mo, parse):
    # --- Recipe: Classify statement type ---
    _sql = "SELECT 1; INSERT INTO logs (msg) VALUES ('hello'); CREATE TABLE events (id int, name text)"
    _tree = parse(_sql)

    _classifications = []
    for _raw_stmt in _tree.stmts:
        _stmt_type = _raw_stmt.stmt.WhichOneof("node")
        _classifications.append(_stmt_type)

    _rows = "\n".join(f"| {i + 1} | `{t}` |" for i, t in enumerate(_classifications))
    mo.md(
        f"""
        ## Recipe 3: Classify Statement Type

        Inspects the `stmt` oneof field of each `RawStmt` to identify the
        top-level statement type.

        **SQL:**
        ```sql
        {_sql}
        ```

        | # | Statement Type |
        |---|----------------|
        {_rows}
        """
    )
    return


@app.cell
def _(mo, parse, walk):
    # --- Recipe: Detect subqueries ---
    _sql = "SELECT * FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE region = 'west') AND total > (SELECT AVG(total) FROM orders)"
    _tree = parse(_sql)

    _subqueries = []
    _first = True
    for _field_name, _msg in walk(_tree):
        if type(_msg).__name__ == "SelectStmt":
            if _first:
                _first = False  # skip top-level SelectStmt
            else:
                _subqueries.append(_field_name)

    mo.md(
        f"""
        ## Recipe 4: Detect Subqueries

        Uses `walk()` to find nested `SelectStmt` nodes below the top-level
        statement. The first `SelectStmt` is the main query; subsequent ones are
        subqueries.

        **SQL:**
        ```sql
        {_sql}
        ```

        **Subqueries found:** {len(_subqueries)}

        | # | Reached via field |
        |---|-------------------|
        """
        + "\n".join(f"| {i + 1} | `{f}` |" for i, f in enumerate(_subqueries))
    )
    return


@app.cell
def _(mo, parse, walk):
    # --- Recipe: Measure query complexity ---
    _queries = {
        "simple": "SELECT 1",
        "complex": "SELECT o.id, c.name, p.title FROM orders o JOIN customers c ON o.cid = c.id JOIN products p ON o.pid = p.id WHERE o.total > 100 AND c.active = true AND p.stock > 0",
    }

    def _measure_complexity(sql):
        _tree = parse(sql)
        _total_nodes = 0
        _joins = 0
        _conditions = 0
        for _fn, _msg in walk(_tree):
            _total_nodes += 1
            _name = type(_msg).__name__
            if _name == "JoinExpr":
                _joins += 1
            elif _name in ("BoolExpr", "A_Expr"):
                _conditions += 1
        return {
            "nodes": _total_nodes,
            "joins": _joins,
            "conditions": _conditions,
            "score": _total_nodes + _joins * 5 + _conditions * 3,
        }

    _results = {label: _measure_complexity(sql) for label, sql in _queries.items()}

    _rows = "\n".join(
        f"| {label} | {r['nodes']} | {r['joins']} | {r['conditions']} | **{r['score']}** |"
        for label, r in _results.items()
    )
    mo.md(
        f"""
        ## Recipe 5: Measure Query Complexity

        Counts total AST nodes, `JoinExpr` joins, and `BoolExpr`/`A_Expr`
        conditions to produce a weighted complexity score.

        | Query | Nodes | Joins | Conditions | Score |
        |-------|-------|-------|------------|-------|
        {_rows}
        """
    )
    return


@app.cell
def _(Visitor, mo, parse):
    # --- Recipe: Map schema dependencies ---
    _sql = """
    CREATE TABLE customers (id int, name text);
    CREATE TABLE orders (id int, customer_id int, total int);
    INSERT INTO orders SELECT nextval('order_seq'), id, 0 FROM customers;
    CREATE TABLE reports AS SELECT c.name, SUM(o.total) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name;
    """
    _tree = parse(_sql)

    _edges = []
    for _raw_stmt in _tree.stmts:
        _stmt_type = _raw_stmt.stmt.WhichOneof("node")
        _node = getattr(_raw_stmt.stmt, _stmt_type)

        class _DepCollector(Visitor):
            def __init__(self):
                self.tables = []

            def visit_RangeVar(self, rv):
                self.tables.append(rv.relname)

        _dc = _DepCollector()
        _dc.visit(_node)

        if _stmt_type == "insert_stmt" and len(_dc.tables) >= 2:
            _target = _dc.tables[0]
            for _source in _dc.tables[1:]:
                _edges.append((_target, _source))
        elif _stmt_type == "create_stmt" and len(_dc.tables) >= 2:
            _target = _dc.tables[0]
            for _source in _dc.tables[1:]:
                _edges.append((_target, _source))

    _edge_rows = "\n".join(f"| `{t}` | `{s}` |" for t, s in _edges)
    mo.md(
        f"""
        ## Recipe 6: Map Schema Dependencies

        Parses DDL and DML statements, extracts table names per statement, and
        identifies dependency edges (table A depends on table B).

        **SQL:**
        ```sql
        {_sql.strip()}
        ```

        | Target | Depends On |
        |--------|------------|
        {_edge_rows}
        """
    )
    return


if __name__ == "__main__":
    app.run()
