"""Error handling for postgast.

Provides the public PgQueryError exception and an internal helper to raise it from C result structs returned by
libpg_query.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctypes import Structure


class PgQueryError(Exception):
    """Structured error raised when libpg_query rejects a SQL statement.

    Every postgast function that calls into libpg_query (:func:`~postgast.parse`,
    :func:`~postgast.deparse`, :func:`~postgast.normalize`, :func:`~postgast.fingerprint`,
    :func:`~postgast.split`, :func:`~postgast.scan`, :func:`~postgast.parse_plpgsql`, and
    :func:`~postgast.format_sql`) may raise this exception.  The error carries the
    same structured fields that the C library provides, so callers can build precise
    diagnostics (e.g., underlining the offending token) without parsing the message
    string.

    ``cursorpos`` is a **1-based byte offset** into the original SQL string pointing to
    the token where the error was detected.  When it is ``0`` the position is unknown.
    Convert it to a 0-based Python index with ``e.cursorpos - 1`` when slicing.

    The ``funcname``, ``filename``, and ``lineno`` fields refer to the *internal C
    source* of libpg_query / PostgreSQL's parser, not to your Python code.  They are
    mainly useful for filing upstream bug reports.

    Attributes:
        message: Human-readable error description from the PostgreSQL parser.
        cursorpos: 1-based byte offset in the SQL string where the error was detected
            (``0`` when the position is unavailable).
        context: Additional context from the parser (e.g., PL/pgSQL function name), or
            ``None``.
        funcname: Internal C function name where the error originated, or ``None``.
        filename: Internal C source file where the error originated, or ``None``.
        lineno: Line number in the internal C source file (``0`` when unavailable).

    Examples:
        Catch a syntax error and inspect the cursor position:

        >>> from postgast import parse, PgQueryError
        >>> try:
        ...     parse("SELECT FROM")
        ... except PgQueryError as e:
        ...     print(e.cursorpos)
        8

        Use ``cursorpos`` to highlight the error location:

        >>> from postgast import parse, PgQueryError
        >>> sql = "SELECT * FORM users"
        >>> try:
        ...     parse(sql)
        ... except PgQueryError as e:
        ...     idx = max(e.cursorpos - 1, 0)
        ...     print(sql)
        ...     print(" " * idx + "^")
        ...     print(e.message)
        SELECT * FORM users
                 ^
        syntax error at or near "FORM"
    """

    def __init__(
        self,
        message: str,
        *,
        cursorpos: int = 0,
        context: str | None = None,
        funcname: str | None = None,
        filename: str | None = None,
        lineno: int = 0,
    ) -> None:
        """Create a PgQueryError.

        Args:
            message: Human-readable error description.
            cursorpos: 1-based position in the SQL string where the error was detected.
            context: Additional parser context.
            funcname: Internal C function name where the error originated.
            filename: Internal C source file.
            lineno: Line number in the C source file.
        """
        super().__init__(message)
        self.message = message
        self.cursorpos = cursorpos
        self.context = context
        self.funcname = funcname
        self.filename = filename
        self.lineno = lineno


def check_error(result: Structure) -> None:
    """Inspect a C result struct's error pointer and raise if set.

    If the error pointer is non-null, extracts the error fields and raises ``PgQueryError``. The caller is responsible
    for freeing the C result (typically via a ``finally`` block).

    Args:
        result: A ctypes Structure with an ``error`` field (pointer to PgQueryError C struct).
    """
    err_ptr = result.error
    if not err_ptr:
        return

    err = err_ptr.contents
    message = err.message.decode("utf-8") if err.message else "unknown error"
    context = err.context.decode("utf-8") if err.context else None
    funcname = err.funcname.decode("utf-8") if err.funcname else None
    filename = err.filename.decode("utf-8") if err.filename else None

    raise PgQueryError(
        message,
        cursorpos=err.cursorpos,
        context=context,
        funcname=funcname,
        filename=filename,
        lineno=err.lineno,
    )
