"""SQL query deparsing via libpg_query."""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

from postgast.errors import check_error
from postgast.native import PgQueryProtobuf, lib
from postgast.nodes.base import AstNode

if TYPE_CHECKING:
    from google.protobuf.message import Message

    from postgast.pg_query_pb2 import ParseResult


def deparse(tree: ParseResult | AstNode) -> str:
    """Convert a protobuf parse tree back into a SQL string.

    Calls libpg_query's ``pg_query_deparse_protobuf`` to convert a ``ParseResult`` AST back into SQL text. This is the
    inverse of :func:`postgast.parse`.

    Note:
        The deparsed SQL is canonicalized by libpg_query and may differ from the original query in whitespace, casing,
        or parenthesization while remaining semantically equivalent.

    Args:
        tree: A ``ParseResult`` protobuf message (as returned by :func:`postgast.parse`), or a typed ``AstNode``
            wrapper.

    Returns:
        The deparsed SQL string.

    Raises:
        PgQueryError: If the parse tree cannot be deparsed.

    Example:
        >>> from postgast import parse, deparse
        >>> tree = parse("SELECT id FROM users")
        >>> deparse(tree)
        'SELECT id FROM users'
    """
    pb: Message = tree._pb if isinstance(tree, AstNode) else tree  # pyright: ignore[reportPrivateUsage]
    data = pb.SerializeToString()
    buf = ctypes.create_string_buffer(data)
    pbuf = PgQueryProtobuf(len=len(data), data=ctypes.cast(buf, ctypes.c_void_p).value)
    result = lib.pg_query_deparse_protobuf(pbuf)
    try:
        check_error(result)
        query: bytes = result.query
        return query.decode("utf-8")
    finally:
        lib.pg_query_free_deparse_result(result)
