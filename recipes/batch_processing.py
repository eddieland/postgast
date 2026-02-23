"""Batch Processing Recipebook — interactive examples for multi-statement and multi-query workflows with postgast."""

from __future__ import annotations

from typing import TYPE_CHECKING

import marimo

if TYPE_CHECKING:
    import types
    from collections.abc import Callable, Generator

    from google.protobuf.message import Message

    from postgast import FingerprintResult, ParseResult, PgQueryError
    from postgast.pg_query_pb2 import ScanResult

__generated_with = "0.19.11"
app = marimo.App()


@app.cell
def _(mo: types.ModuleType):
    mo.md("""
    # Batch Processing Recipebook

    Interactive recipes demonstrating how to process multi-statement SQL,
    analyze query logs, and build automated pipelines using **postgast**.

    Each recipe is self-contained: it defines a SQL input, runs processing
    code, and displays the results.

    **How to use this notebook:**

    - `marimo run recipes/batch_processing.py` — read-only app mode
    - `marimo edit recipes/batch_processing.py` — interactive editing mode
    """)
    return


@app.cell
def _():
    import marimo as mo

    from postgast import (
        PgQueryError,
        extract_functions,
        extract_tables,
        find_nodes,
        fingerprint,
        normalize,
        parse,
        pg_query_pb2,
        scan,
        split,
    )

    return (
        PgQueryError,
        extract_functions,
        extract_tables,
        find_nodes,
        fingerprint,
        mo,
        normalize,
        parse,
        pg_query_pb2,
        scan,
        split,
    )


@app.cell
def _(
    extract_tables: Callable[[Message], list[str]],
    mo: types.ModuleType,
    parse: Callable[[str], ParseResult],
    split: Callable[[str], list[str]],
):
    # --- Recipe: Split and parse a migration file ---
    _migration = """
    CREATE TABLE departments (id serial PRIMARY KEY, name text NOT NULL);
    CREATE INDEX idx_departments_name ON departments (name);
    ALTER TABLE departments ADD COLUMN budget numeric DEFAULT 0;
    INSERT INTO departments (name, budget) SELECT division, sum(cost) FROM legacy_orgs GROUP BY division;
    """

    _statements = split(_migration)

    _rows: list[str] = []
    for _i, _stmt_sql in enumerate(_statements):
        _tree = parse(_stmt_sql)
        _stmt_type = _tree.stmts[0].stmt.WhichOneof("node")
        _tables = extract_tables(_tree)
        _preview = _stmt_sql.strip()[:60]
        if len(_stmt_sql.strip()) > 60:
            _preview += "..."
        _rows.append(
            f"| {_i + 1} | `{_stmt_type}` | {', '.join(f'`{t}`' for t in set(_tables)) or '---'} | `{_preview}` |"
        )

    _table_rows = "\n".join(_rows)
    mo.md(
        f"""
        ## Recipe 1: Split and Parse a Migration File

        `split` divides a multi-statement migration into individual statements,
        then `parse` analyzes each one.  This is the foundation for any
        multi-statement processing pipeline.

        **{len(_statements)} statements found:**

        | # | Type | Tables | SQL Preview |
        |---|------|--------|-------------|
        {_table_rows}
        """
    )
    return


@app.cell
def _(
    mo: types.ModuleType,
    pg_query_pb2: types.ModuleType,
    scan: Callable[[str], ScanResult],
):
    # --- Recipe: SQL tokenization and keyword map ---
    _sql = "SELECT u.name, COUNT(*) AS total FROM users u WHERE u.active = true GROUP BY u.name"
    _result = scan(_sql)
    _sql_bytes = _sql.encode("utf-8")

    _token_rows: list[str] = []
    for _tok in _result.tokens:
        _text = _sql_bytes[_tok.start : _tok.end].decode("utf-8")
        _token_name = pg_query_pb2.Token.Name(_tok.token)
        _kw_kind = pg_query_pb2.KeywordKind.Name(_tok.keyword_kind)
        _token_rows.append(f"| `{_text}` | `{_token_name}` | `{_kw_kind}` | {_tok.start}--{_tok.end} |")

    _token_table = "\n".join(_token_rows)

    # Summary by keyword kind
    from collections import Counter

    _kw_counts = Counter(pg_query_pb2.KeywordKind.Name(_tok.keyword_kind) for _tok in _result.tokens)
    _summary_rows = "\n".join(f"| `{kind}` | {count} |" for kind, count in _kw_counts.most_common())

    mo.md(
        f"""
        ## Recipe 2: SQL Tokenization and Keyword Map

        `scan` tokenizes SQL into a list of tokens with type, keyword kind, and
        byte positions.  This is useful for syntax highlighting, linting, and
        understanding how PostgreSQL's lexer sees your SQL.

        **SQL:** `{_sql}`

        | Text | Token | Keyword Kind | Bytes |
        |------|-------|-------------|-------|
        {_token_table}

        **Token summary by keyword kind:**

        | Kind | Count |
        |------|-------|
        {_summary_rows}
        """
    )
    return


@app.cell
def _(
    extract_tables: Callable[[Message], list[str]],
    fingerprint: Callable[[str], FingerprintResult],
    mo: types.ModuleType,
    normalize: Callable[[str], str],
    parse: Callable[[str], ParseResult],
):
    # --- Recipe: Query log deduplication pipeline ---
    _query_log = [
        "SELECT * FROM users WHERE id = 42",
        "SELECT name, email FROM users WHERE active = true",
        "INSERT INTO events (type, user_id) VALUES ('login', 5)",
        "SELECT * FROM users WHERE id = 100",
        "SELECT * FROM orders WHERE customer_id = 7 AND status = 'shipped'",
        "INSERT INTO events (type, user_id) VALUES ('pageview', 12)",
        "SELECT name, email FROM users WHERE active = false",
        "SELECT * FROM users WHERE id = 3",
        "SELECT * FROM orders WHERE customer_id = 99 AND status = 'pending'",
        "INSERT INTO events (type, user_id) VALUES ('logout', 5)",
        "SELECT name, email FROM users WHERE active = true",
        "SELECT * FROM orders WHERE customer_id = 15 AND status = 'shipped'",
    ]

    _counts: dict[str, int] = {}
    _normalized: dict[str, str] = {}
    _tables_by_fp: dict[str, set[str]] = {}
    for _q in _query_log:
        _fp = fingerprint(_q).hex
        _counts[_fp] = _counts.get(_fp, 0) + 1
        _normalized[_fp] = normalize(_q)
        _tables_by_fp.setdefault(_fp, set()).update(extract_tables(parse(_q)))

    # Sort by count descending
    _sorted_fps = sorted(_counts, key=lambda fp: _counts[fp], reverse=True)

    _rows = "\n".join(
        f"| {_counts[fp]} | `{fp[:16]}...` | {', '.join(f'`{t}`' for t in _tables_by_fp[fp])} | `{_normalized[fp]}` |"
        for fp in _sorted_fps
    )
    mo.md(
        f"""
        ## Recipe 3: Query Log Deduplication Pipeline

        Combine `normalize` + `fingerprint` to deduplicate a simulated query log.
        Queries are grouped by structural fingerprint, then counted and displayed
        with their normalized template.

        **{len(_query_log)} queries -> {len(_counts)} unique patterns**

        | Count | Fingerprint | Tables | Normalized Template |
        |-------|-------------|--------|---------------------|
        {_rows}
        """
    )
    return


@app.cell
def _(
    find_nodes: Callable[[Message, type[Message]], Generator[Message, None, None]],
    mo: types.ModuleType,
    parse: Callable[[str], ParseResult],
    split: Callable[[str], list[str]],
):
    # --- Recipe: Migration dependency graph ---
    from postgast.pg_query_pb2 import Constraint as _Constraint

    _schema_sql = """
    CREATE TABLE departments (id serial PRIMARY KEY, name text NOT NULL);
    CREATE TABLE employees (id serial PRIMARY KEY, name text, dept_id int REFERENCES departments(id));
    CREATE TABLE projects (id serial PRIMARY KEY, title text, lead_id int REFERENCES employees(id));
    CREATE TABLE assignments (id serial, emp_id int REFERENCES employees(id), proj_id int REFERENCES projects(id));
    """

    _statements = split(_schema_sql)

    _deps: dict[str, set[str]] = {}
    for _stmt_sql in _statements:
        _tree = parse(_stmt_sql)
        _stmt_type = _tree.stmts[0].stmt.WhichOneof("node")
        if _stmt_type != "create_stmt":
            continue
        _node = getattr(_tree.stmts[0].stmt, _stmt_type)
        _table_name: str = _node.relation.relname  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        _fk_refs: set[str] = set()
        for _constraint in find_nodes(_node, _Constraint):
            if _constraint.HasField("pktable") and _constraint.pktable.relname:  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
                _fk_refs.add(_constraint.pktable.relname)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
        _deps[_table_name] = _fk_refs

    # Topological sort (Kahn's algorithm)
    from collections import deque

    _in_degree = {t: len(d & set(_deps)) for t, d in _deps.items()}
    _queue = deque(t for t, d in _in_degree.items() if d == 0)
    _order: list[str] = []
    while _queue:
        _t = _queue.popleft()
        _order.append(_t)
        for _other, _other_deps in _deps.items():
            if _t in _other_deps:
                _in_degree[_other] -= 1
                if _in_degree[_other] == 0:
                    _queue.append(_other)

    _dep_rows = "\n".join(
        f"| `{table}` | {', '.join(f'`{d}`' for d in deps) or '---'} |" for table, deps in _deps.items()
    )
    mo.md(
        f"""
        ## Recipe 4: Migration Dependency Graph

        Parses CREATE TABLE statements, extracts REFERENCES (foreign key)
        constraints, and builds a dependency graph.  A topological sort
        determines the safe creation order.

        **Dependencies:**

        | Table | Depends On |
        |-------|------------|
        {_dep_rows}

        **Safe creation order:** {" -> ".join(f"`{t}`" for t in _order)}
        """
    )
    return


@app.cell
def _(
    mo: types.ModuleType,
    pg_query_pb2: types.ModuleType,
    scan: Callable[[str], ScanResult],
):
    # --- Recipe: Comment extraction via scanner ---
    _sql = """\
-- Fetch active users and their order totals
SELECT
    u.name,
    /* full name from profile */
    u.email,
    SUM(o.total) AS lifetime_value
FROM users u
JOIN orders o ON u.id = o.user_id  -- link via user ID
WHERE u.active = true
/* only include users with at least one order */
GROUP BY u.name, u.email
"""

    _result = scan(_sql)
    _sql_bytes = _sql.encode("utf-8")

    _comments: list[tuple[str, int, int, str]] = []
    for _tok in _result.tokens:
        _token_name = pg_query_pb2.Token.Name(_tok.token)
        if _token_name in ("SQL_COMMENT", "C_COMMENT"):
            _text = _sql_bytes[_tok.start : _tok.end].decode("utf-8")
            _comments.append((_token_name, _tok.start, _tok.end, _text))

    _comment_rows = "\n".join(
        f"| `{kind}` | {start}--{end} | `{text.strip()[:50]}` |" for kind, start, end, text in _comments
    )

    # Reconstruct SQL without comments
    _parts: list[bytes] = []
    _pos = 0
    for _, _start, _end, _ in _comments:
        _parts.append(_sql_bytes[_pos:_start])
        _pos = _end
    _parts.append(_sql_bytes[_pos:])
    _stripped = b"".join(_parts).decode("utf-8")

    import re

    _stripped = re.sub(r"\n\s*\n", "\n", _stripped).strip()

    mo.md(
        f"""
        ## Recipe 5: Comment Extraction via Scanner

        `scan` identifies `SQL_COMMENT` (`--`) and `C_COMMENT` (`/* */`) tokens.
        Their byte positions let us extract comment text and reconstruct the SQL
        with comments stripped.

        **{len(_comments)} comments found:**

        | Type | Bytes | Text |
        |------|-------|------|
        {_comment_rows}

        **SQL with comments stripped:**

        ```sql
        {_stripped}
        ```
        """
    )
    return


@app.cell
def _(
    PgQueryError: type[PgQueryError],
    extract_functions: Callable[[Message], list[str]],
    extract_tables: Callable[[Message], list[str]],
    mo: types.ModuleType,
    parse: Callable[[str], ParseResult],
    split: Callable[[str], list[str]],
):
    # --- Recipe: Safe batch execution plan ---
    _batch_sql = """
    SELECT COUNT(*) FROM users;
    UPDATE orders SET status = 'archived' WHERE created < '2024-01-01';
    SELECT * FROM broken_syntax;
    DROP TABLE temp_imports;
    INSERT INTO audit_log (action) VALUES ('batch_run');
    CREATE INDEX idx_orders_status ON orders (status);
    """

    _RISK: dict[str, str] = {
        "select_stmt": "SAFE",
        "index_stmt": "SAFE",
        "create_stmt": "SAFE",
        "insert_stmt": "CAUTION",
        "update_stmt": "CAUTION",
        "delete_stmt": "UNSAFE",
        "drop_stmt": "UNSAFE",
        "truncate_stmt": "UNSAFE",
    }

    _statements = split(_batch_sql)

    _plan: list[dict[str, object]] = []
    for _i, _stmt_sql in enumerate(_statements):
        try:
            _tree = parse(_stmt_sql)
            _stmt_type = _tree.stmts[0].stmt.WhichOneof("node")
            _risk = _RISK.get(_stmt_type or "", "CAUTION")
            _tables = extract_tables(_tree)
            _funcs = extract_functions(_tree)
            _plan.append({
                "num": _i + 1,
                "sql": _stmt_sql.strip()[:50],
                "type": _stmt_type,
                "risk": _risk,
                "tables": _tables,
                "functions": _funcs,
                "error": None,
            })
        except PgQueryError as _e:
            _plan.append({
                "num": _i + 1,
                "sql": _stmt_sql.strip()[:50],
                "type": "---",
                "risk": "ERROR",
                "tables": [],
                "functions": [],
                "error": _e.message,
            })

    _rows: list[str] = []
    for _entry in _plan:
        _tbl_str = ", ".join(f"`{t}`" for t in set(_entry["tables"])) or "---"  # pyright: ignore[reportUnknownVariableType, reportArgumentType]
        _rows.append(
            f"| {_entry['num']} | **{_entry['risk']}** | `{_entry['type']}` | {_tbl_str} | `{_entry['sql']}` |"
        )

    _table_rows = "\n".join(_rows)

    _safe = sum(1 for e in _plan if e["risk"] == "SAFE")
    _caution = sum(1 for e in _plan if e["risk"] == "CAUTION")
    _unsafe = sum(1 for e in _plan if e["risk"] == "UNSAFE")
    _errors = sum(1 for e in _plan if e["risk"] == "ERROR")

    _error_section = ""
    if _errors > 0:
        _error_lines = "\n".join(f"- Statement {e['num']}: {e['error']}" for e in _plan if e["error"])
        _error_section = f"\n\n**Parse errors:**\n{_error_lines}"

    mo.md(
        f"""
        ## Recipe 6: Safe Batch Execution Plan

        The culminating recipe: split a raw SQL batch, parse each statement,
        classify by risk level, extract metadata, and handle parse errors
        gracefully.  Produces an execution plan report.

        **Summary:** {_safe} safe, {_caution} caution, {_unsafe} unsafe, {_errors} error(s)

        | # | Risk | Type | Tables | SQL |
        |---|------|------|--------|-----|
        {_table_rows}
        """
        + _error_section
    )
    return


if __name__ == "__main__":
    app.run()
