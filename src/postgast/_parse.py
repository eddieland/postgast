"""SQL query parsing via libpg_query."""

from __future__ import annotations

import ctypes

from postgast._errors import check_error
from postgast._native import lib
from postgast._pg_query_pb2 import ParseResult


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
    """
    result = lib.pg_query_parse_protobuf(query.encode("utf-8"))
    try:
        check_error(result)
        pbuf = result.parse_tree
        data = ctypes.string_at(pbuf.data, pbuf.len)
        return ParseResult.FromString(data)
    finally:
        lib.pg_query_free_protobuf_parse_result(result)
