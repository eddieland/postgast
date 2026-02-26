"""SQL pretty-printer that walks the protobuf AST and emits formatted SQL."""

from __future__ import annotations

from typing import TYPE_CHECKING

from postgast.format.base import _SqlFormatterBase  # pyright: ignore[reportPrivateUsage]
from postgast.format.ddl import _DdlMixin  # pyright: ignore[reportPrivateUsage]
from postgast.format.dml import _DmlMixin  # pyright: ignore[reportPrivateUsage]
from postgast.format.expressions import _ExpressionMixin  # pyright: ignore[reportPrivateUsage]
from postgast.format.select import _SelectMixin  # pyright: ignore[reportPrivateUsage]
from postgast.parse import parse
from postgast.walk import _unwrap_node  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from postgast.pg_query_pb2 import ParseResult


class _SqlFormatter(_ExpressionMixin, _SelectMixin, _DmlMixin, _DdlMixin, _SqlFormatterBase):
    """AST visitor that emits formatted SQL."""


def format_sql(sql: str | ParseResult) -> str:
    """Format a SQL string or ParseResult into a canonical, readable layout.

    Args:
        sql: A SQL string or an already-parsed ``ParseResult``.

    Returns:
        A pretty-printed SQL string with uppercase keywords, clause-per-line layout, and indented bodies. Each statement
        ends with a semicolon.

    Raises:
        PgQueryError: If *sql* is a string that cannot be parsed.
    """
    tree: ParseResult = parse(sql) if isinstance(sql, str) else sql
    formatter = _SqlFormatter()
    parts: list[str] = []
    for raw_stmt in tree.stmts:
        stmt = _unwrap_node(raw_stmt.stmt)
        formatter.reset()
        formatter.visit(stmt)
        parts.append(formatter.get_output())
    return ";\n\n".join(parts) + ";" if parts else ""
