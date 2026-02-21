"""SQL Transforms Recipebook — interactive examples for transforming and analyzing SQL with postgast."""

import marimo

__generated_with = "0.19.11"
app = marimo.App()


@app.cell
def _(mo):
    mo.md("""
    # SQL Transforms Recipebook

    Interactive recipes demonstrating how to transform, normalize, compare, and
    rewrite SQL using **postgast**.

    Each recipe is self-contained: it defines a SQL input, runs transformation
    code, and displays the results.

    **How to use this notebook:**

    - `marimo run recipes/sql_transforms.py` — read-only app mode
    - `marimo edit recipes/sql_transforms.py` — interactive editing mode
    """)
    return


@app.cell
def _():
    import marimo as mo

    from postgast import (
        PgQueryError,
        deparse,
        ensure_or_replace,
        find_nodes,
        fingerprint,
        normalize,
        parse,
        set_or_replace,
    )

    return PgQueryError, deparse, ensure_or_replace, find_nodes, fingerprint, mo, normalize, parse, set_or_replace


@app.cell
def _(deparse, mo, parse):
    # --- Recipe: Parse-deparse roundtrip ---
    _variants = [
        "select   id,name   from   users   where  active  =  true",
        "SELECT ID, NAME FROM USERS WHERE ACTIVE = TRUE",
        "SELECT\n  id,\n  name\nFROM\n  users\nWHERE\n  active = true",
    ]

    _canonical = [deparse(parse(v)) for v in _variants]

    _rows = "\n".join(f"| `{v.replace(chr(10), ' ')}` | `{c}` |" for v, c in zip(_variants, _canonical, strict=True))
    mo.md(
        f"""
        ## Recipe 1: Parse-Deparse Roundtrip

        Feeding cosmetically different SQL variants through `parse` then `deparse`
        produces identical canonical output — proof that the roundtrip
        normalizes whitespace, casing, and formatting.

        | Input | Canonical Output |
        |-------|-----------------|
        {_rows}

        **All identical?** `{len(set(_canonical)) == 1}`
        """
    )
    return


@app.cell
def _(mo, normalize):
    # --- Recipe: Normalize queries for log analysis ---
    _log_queries = [
        "SELECT * FROM users WHERE id = 42",
        "SELECT * FROM users WHERE id = 99",
        "SELECT * FROM users WHERE id = 7",
        "INSERT INTO logs (msg, level) VALUES ('user login', 'info')",
        "INSERT INTO logs (msg, level) VALUES ('page view', 'debug')",
        "SELECT name, email FROM users WHERE active = true AND created > '2024-01-01'",
        "SELECT name, email FROM users WHERE active = true AND created > '2025-06-15'",
    ]

    from collections import Counter

    _templates = [normalize(q) for q in _log_queries]
    _counts = Counter(_templates)

    _rows = "\n".join(f"| {count} | `{template}` |" for template, count in _counts.most_common())
    mo.md(
        f"""
        ## Recipe 2: Normalize Queries for Log Analysis

        `normalize` strips literal values and replaces them with positional
        placeholders (`$1`, `$2`, ...).  Grouping by the normalized template
        reveals query patterns in application logs.

        **{len(_log_queries)} log queries -> {len(_counts)} unique templates**

        | Count | Normalized Template |
        |-------|---------------------|
        {_rows}
        """
    )
    return


@app.cell
def _(fingerprint, mo, normalize):
    # --- Recipe: Fingerprint for structural equivalence ---
    _queries = [
        "SELECT * FROM users WHERE id = 1",
        "select * from users where id = 999",
        "SELECT * FROM  users  WHERE  id = 42",
        "SELECT name FROM orders WHERE total > 100",
        "SELECT name FROM orders WHERE total > 50",
        "INSERT INTO events (type) VALUES ('click')",
        "INSERT INTO events (type) VALUES ('view')",
    ]

    _results = [(q, fingerprint(q), normalize(q)) for q in _queries]

    from collections import defaultdict

    _groups = defaultdict(list)
    for _q, _fp, _norm in _results:
        _groups[_fp.hex].append((_q, _norm))

    _sections = []
    for _hex, _members in _groups.items():
        _member_rows = "\n".join(f"| `{q}` | `{n}` |" for q, n in _members)
        _sections.append(
            f"**Fingerprint `{_hex[:16]}...`** ({len(_members)} queries)\n\n"
            f"| Query | Normalized |\n|-------|------------|\n{_member_rows}"
        )

    mo.md(
        "## Recipe 3: Fingerprint for Structural Equivalence\n\n"
        "`fingerprint` produces a hash that groups structurally equivalent queries "
        "regardless of literals or formatting.  Unlike `normalize` (which produces a "
        "template string), fingerprint gives a fixed-length identifier.\n\n" + "\n\n".join(_sections)
    )
    return


@app.cell
def _(deparse, find_nodes, mo, parse):
    # --- Recipe: Query rewriting via AST modification ---
    _sql = "SELECT id, name FROM users WHERE active = true"

    # Transform 1: Add schema prefix
    _tree1 = parse(_sql)
    for _rv in find_nodes(_tree1, "RangeVar"):
        _rv.schemaname = "public"
    _schema_prefixed = deparse(_tree1)

    # Transform 2: Rename table
    _tree2 = parse(_sql)
    for _rv in find_nodes(_tree2, "RangeVar"):
        if _rv.relname == "users":
            _rv.relname = "app_users"
    _renamed = deparse(_tree2)

    # Transform 3: Both
    _tree3 = parse(_sql)
    for _rv in find_nodes(_tree3, "RangeVar"):
        _rv.schemaname = "myapp"
        if _rv.relname == "users":
            _rv.relname = "app_users"
    _both = deparse(_tree3)

    mo.md(
        f"""
        ## Recipe 4: Query Rewriting via AST Modification

        Parse SQL into a mutable protobuf AST, modify node fields, then deparse
        back to SQL.  This demonstrates direct tree surgery for automated query
        rewriting.

        **Original:** `{_sql}`

        | Transform | Result |
        |-----------|--------|
        | Add schema prefix | `{_schema_prefixed}` |
        | Rename `users` -> `app_users` | `{_renamed}` |
        | Both transforms | `{_both}` |
        """
    )
    return


@app.cell
def _(deparse, ensure_or_replace, mo, parse, set_or_replace):
    # --- Recipe: Ensure OR REPLACE ---
    _statements = [
        "CREATE FUNCTION greet(text) RETURNS text AS $$ SELECT 'hello ' || $1 $$ LANGUAGE sql",
        "CREATE VIEW active_users AS SELECT * FROM users WHERE active = true",
        "CREATE TRIGGER audit_trigger BEFORE INSERT ON orders FOR EACH ROW EXECUTE FUNCTION audit_fn()",
        "CREATE TABLE events (id serial, name text)",
    ]

    _results = []
    for _stmt in _statements:
        _tree = parse(_stmt)
        _count = set_or_replace(_tree)
        _rewritten = deparse(_tree)
        _orig_display = _stmt[:60] + "..." if len(_stmt) > 60 else _stmt
        _result_display = _rewritten[:80] + "..." if len(_rewritten) > 80 else _rewritten
        _results.append((_orig_display, _count > 0, _result_display))

    _rows = "\n".join(f"| `{orig}` | {'Yes' if changed else 'No'} | `{result}` |" for orig, changed, result in _results)

    # Also show the all-in-one ensure_or_replace function
    _combined = ";\n".join(_statements[:3])
    _combined_result = ensure_or_replace(_combined)

    mo.md(
        f"""
        ## Recipe 5: Ensure OR REPLACE

        `set_or_replace` flips the `replace` flag on eligible DDL nodes
        (functions, views, triggers).  `ensure_or_replace` wraps this in a
        parse -> modify -> deparse pipeline for convenience.

        **Per-statement results:**

        | Original | Rewritten? | Result |
        |----------|-----------|--------|
        {_rows}

        *Note: CREATE TABLE is not eligible — only FUNCTION, VIEW, and TRIGGER
        support OR REPLACE.*

        **Batch `ensure_or_replace` output:**

        ```sql
        {_combined_result}
        ```
        """
    )
    return


@app.cell
def _(PgQueryError, mo, parse):
    # --- Recipe: Structured error inspection ---
    _broken_queries = [
        ("Missing table name", "SELECT * FROM"),
        ("Unterminated string", "SELECT 'hello"),
        ("Unexpected token", "SELECT 1 + FROM users"),
        ("Bad column list", "SELECT , FROM users"),
    ]

    _sections = []
    for _label, _sql in _broken_queries:
        try:
            parse(_sql)
            _sections.append(f"**{_label}:** `{_sql}` — No error (unexpected!)")
        except PgQueryError as _e:
            _block = f"**{_label}**\n```\n{_sql}\n"
            if _e.cursorpos > 0:
                _block += " " * (_e.cursorpos - 1) + "^^^\n"
            _block += f"```\nError: {_e.message}"
            if _e.cursorpos > 0:
                _block += f" (position {_e.cursorpos})"
            _sections.append(_block)

    mo.md(
        "## Recipe 6: Structured Error Inspection\n\n"
        "`PgQueryError` provides the error message, cursor position, and "
        "context from the PostgreSQL parser.  The cursor position enables "
        "precise visual `^^^` error markers.\n\n" + "\n\n".join(_sections)
    )
    return


if __name__ == "__main__":
    app.run()
