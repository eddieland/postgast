"""SQL query deparsing via libpg_query."""

from __future__ import annotations

from postgast._errors import check_error
from postgast._native import PgQueryProtobuf, lib
from postgast._pg_query_pb2 import ParseResult


def deparse(tree: ParseResult) -> str:
    """Convert a protobuf parse tree back into a SQL string.

    Calls libpg_query's ``pg_query_deparse_protobuf`` to convert a
    ``ParseResult`` AST back into SQL text. This is the inverse of
    :func:`postgast.parse`.

    Note:
        The deparsed SQL is canonicalized by libpg_query and may differ from
        the original query in whitespace, casing, or parenthesization while
        remaining semantically equivalent.

    Args:
        tree: A ``ParseResult`` protobuf message (as returned by :func:`postgast.parse`).

    Returns:
        The deparsed SQL string.

    Raises:
        PgQueryError: If the parse tree cannot be deparsed.
    """
    data = tree.SerializeToString()
    pbuf = PgQueryProtobuf(len=len(data), data=data)
    result = lib.pg_query_deparse_protobuf(pbuf)
    try:
        check_error(result)
        query: bytes = result.query
        return query.decode("utf-8")
    finally:
        lib.pg_query_free_deparse_result(result)
