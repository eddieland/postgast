"""PL/pgSQL function parsing via libpg_query."""

from __future__ import annotations

import json
from typing import Any

from postgast.errors import check_error
from postgast.native import lib


def parse_plpgsql(sql: str) -> list[dict[str, Any]]:
    """Parse a PL/pgSQL function into a structured representation.

    Calls libpg_query's ``pg_query_parse_plpgsql`` to parse a
    ``CREATE FUNCTION ... LANGUAGE plpgsql`` statement and returns the
    parsed function body as a list of dictionaries.

    Args:
        sql: A ``CREATE FUNCTION`` statement with ``LANGUAGE plpgsql``.

    Returns:
        A list of dictionaries describing the parsed PL/pgSQL function(s).
        Each dictionary contains keys like ``"PLpgSQL_function"`` with
        nested structure representing declarations, statements, and
        control flow.

    Raises:
        PgQueryError: If the input contains a syntax error.
    """
    result = lib.pg_query_parse_plpgsql(sql.encode("utf-8"))
    try:
        check_error(result)
        json_str = result.plpgsql_funcs.decode("utf-8")
        return json.loads(json_str)
    finally:
        lib.pg_query_free_plpgsql_parse_result(result)
