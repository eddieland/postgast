"""SQL query normalization via libpg_query."""

from __future__ import annotations

from postgast.errors import check_error
from postgast.native import lib


def normalize(query: str) -> str:
    """Normalize a SQL query by replacing literal constants with placeholders.

    Calls libpg_query's ``pg_query_normalize`` to replace literal values
    (strings, numbers, etc.) with parameter placeholders (``$1``, ``$2``, ...).
    This is useful for grouping structurally equivalent queries.

    Args:
        query: A SQL query string.

    Returns:
        The normalized query with constants replaced by positional placeholders.

    Raises:
        PgQueryError: If the query cannot be parsed.

    Example:
        >>> normalize("SELECT * FROM users WHERE id = 42 AND name = 'Alice'")
        'SELECT * FROM users WHERE id = $1 AND name = $2'
    """
    result = lib.pg_query_normalize(query.encode("utf-8"))
    try:
        check_error(result)
        normalized: bytes = result.normalized_query
        return normalized.decode("utf-8")
    finally:
        lib.pg_query_free_normalize_result(result)
