"""SQL query fingerprinting via libpg_query."""

from __future__ import annotations

from typing import NamedTuple

from postgast.errors import check_error
from postgast.native import lib


class FingerprintResult(NamedTuple):
    """Result of fingerprinting a SQL query.

    Attributes:
        fingerprint: The uint64 numeric hash.
        hex: The hexadecimal string representation of the fingerprint.
    """

    fingerprint: int
    hex: str


def fingerprint(query: str) -> FingerprintResult:
    """Compute a structural fingerprint of a SQL query.

    Calls libpg_query's ``pg_query_fingerprint`` to produce a hash that
    identifies structurally equivalent queries regardless of literal values.

    Args:
        query: A SQL query string.

    Returns:
        A ``FingerprintResult`` containing the numeric fingerprint and its
        hex string representation.

    Raises:
        PgQueryError: If the query cannot be parsed.

    Example:
        >>> result = fingerprint("SELECT * FROM users WHERE id = 1")
        >>> result.hex  # doctest: +SKIP
        '0ca858a0484f5826'
        >>> result == fingerprint("SELECT * FROM users WHERE id = 2")
        True
    """
    result = lib.pg_query_fingerprint(query.encode("utf-8"))
    try:
        check_error(result)
        hex_str: bytes = result.fingerprint_str
        return FingerprintResult(fingerprint=result.fingerprint, hex=hex_str.decode("utf-8"))
    finally:
        lib.pg_query_free_fingerprint_result(result)
