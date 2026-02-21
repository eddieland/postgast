"""SQL statement splitting via libpg_query's scanner."""

from __future__ import annotations

from postgast._errors import check_error
from postgast._native import lib


def split(sql: str) -> list[str]:
    """Split a multi-statement SQL string into individual statements.

    Calls libpg_query's ``pg_query_split_with_scanner`` to split the input
    into individual SQL statements. This is a fast, scanner-based operation
    that correctly handles edge cases like comments between statements and
    semicolons inside parenthesized expressions.

    Args:
        sql: A SQL string potentially containing multiple statements.

    Returns:
        A list of individual SQL statement strings.

    Raises:
        PgQueryError: If the SQL causes a scanner error.
    """
    sql_bytes = sql.encode("utf-8")
    result = lib.pg_query_split_with_scanner(sql_bytes)
    try:
        check_error(result)
        stmts: list[str] = []
        for i in range(result.n_stmts):
            stmt = result.stmts[i].contents
            stmts.append(sql_bytes[stmt.stmt_location : stmt.stmt_location + stmt.stmt_len].decode("utf-8"))
        return stmts
    finally:
        lib.pg_query_free_split_result(result)
