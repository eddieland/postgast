"""SQL statement splitting via libpg_query."""

from __future__ import annotations

from typing import Literal

from postgast.errors import check_error
from postgast.native import lib

_SPLIT_METHODS = {
    "scanner": lib.pg_query_split_with_scanner,
    "parser": lib.pg_query_split_with_parser,
}


def split(sql: str, *, method: Literal["scanner", "parser"] = "parser") -> list[str]:
    """Split a multi-statement SQL string into individual statements.

    Calls the selected libpg_query split function to split the input into
    individual SQL statements. The ``"parser"`` method (default) uses the full
    PostgreSQL parser for improved accuracy, while ``"scanner"`` uses a faster
    scanner-based approach that tolerates invalid SQL.

    Args:
        sql: A SQL string potentially containing multiple statements.
        method: Which libpg_query splitter to use. ``"parser"`` (default) calls
            ``pg_query_split_with_parser`` for improved accuracy on valid SQL.
            ``"scanner"`` calls ``pg_query_split_with_scanner``, which tolerates
            malformed SQL but may miss some edge cases.

    Returns:
        A list of individual SQL statement strings.

    Raises:
        PgQueryError: If the SQL causes a parse/scanner error.
        ValueError: If *method* is not ``"scanner"`` or ``"parser"``.
    """
    split_fn = _SPLIT_METHODS.get(method)
    if split_fn is None:
        raise ValueError(f"Unknown split method {method!r}; expected 'scanner' or 'parser'")

    sql_bytes = sql.encode("utf-8")
    result = split_fn(sql_bytes)
    try:
        check_error(result)
        stmts: list[str] = []
        for i in range(result.n_stmts):
            stmt = result.stmts[i].contents
            stmts.append(sql_bytes[stmt.stmt_location : stmt.stmt_location + stmt.stmt_len].decode("utf-8"))
        return stmts
    finally:
        lib.pg_query_free_split_result(result)
