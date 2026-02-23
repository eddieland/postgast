"""SQL query parsing via libpg_query."""

from __future__ import annotations

import ctypes

from postgast.errors import check_error
from postgast.native import lib
from postgast.pg_query_pb2 import ParseResult


def parse(query: str) -> ParseResult:
    """Parse a SQL query into a protobuf AST.

    Calls libpg_query's ``pg_query_parse_protobuf`` to parse the query and
    returns the deserialized ``ParseResult`` protobuf message containing the
    abstract syntax tree.

    Args:
        query: A SQL query string.

    Returns:
        A ``ParseResult`` protobuf message with ``version`` (int) and
        ``stmts`` (list of ``RawStmt``) fields.

    Raises:
        PgQueryError: If the query contains a syntax error.

    Example:
        >>> tree = parse("SELECT id, name FROM users WHERE active = true")
        >>> len(tree.stmts)
        1
        >>> tree.stmts[0].stmt.HasField("select_stmt")
        True
    """
    result = lib.pg_query_parse_protobuf(query.encode("utf-8"))
    try:
        check_error(result)
        pbuf = result.parse_tree
        data = ctypes.string_at(pbuf.data, pbuf.len)
        return ParseResult.FromString(data)
    finally:
        lib.pg_query_free_protobuf_parse_result(result)
