"""Error handling for postgast.

Provides the public PgQueryError exception and an internal helper to raise it
from C result structs returned by libpg_query.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctypes import Structure


class PgQueryError(Exception):
    """Structured error from libpg_query.

    Attributes:
        message: Human-readable error description.
        cursorpos: 1-based position in the SQL string where the error was
            detected (0 if unavailable).
        context: Additional context from the parser, or None.
        funcname: Internal C function name where the error originated, or None.
        filename: Internal C source file, or None.
        lineno: Line number in the C source file.
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
            cursorpos: 1-based position in the SQL string where the
                error was detected.
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

    If the error pointer is non-null, extracts the error fields and raises
    ``PgQueryError``. The caller is responsible for freeing the C result
    (typically via a ``finally`` block).

    Args:
        result: A ctypes Structure with an ``error`` field (pointer to
            PgQueryError C struct).
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
