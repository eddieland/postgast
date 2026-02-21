"""SQL scanning/tokenization via libpg_query."""

from __future__ import annotations

import ctypes

from postgast.errors import check_error
from postgast.native import lib
from postgast.pg_query_pb2 import ScanResult


def scan(sql: str) -> ScanResult:
    """Tokenize a SQL string into a sequence of scan tokens.

    Calls libpg_query's ``pg_query_scan`` to tokenize the input and returns
    the deserialized ``ScanResult`` protobuf message containing a list of
    ``ScanToken`` objects with token type, keyword kind, and byte positions.

    Args:
        sql: A SQL string to tokenize.

    Returns:
        A ``ScanResult`` protobuf message with ``version`` (int) and
        ``tokens`` (list of ``ScanToken``) fields.

    Raises:
        PgQueryError: If the input contains a scan error (e.g., unterminated
            string literal).
    """
    result = lib.pg_query_scan(sql.encode("utf-8"))
    try:
        check_error(result)
        pbuf = result.pbuf
        data = ctypes.string_at(pbuf.data, pbuf.len)
        return ScanResult.FromString(data)
    finally:
        lib.pg_query_free_scan_result(result)
