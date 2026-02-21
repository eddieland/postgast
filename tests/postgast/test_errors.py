import ctypes
from ctypes import POINTER, Structure

import pytest

from postgast._errors import PgQueryError, check_error
from postgast._native import PgQueryError as CPgQueryError


class TestPgQueryError:
    def test_message_attribute(self):
        err = PgQueryError('syntax error at or near "SELEC"', cursorpos=1)
        assert err.message == 'syntax error at or near "SELEC"'

    def test_str_returns_message(self):
        err = PgQueryError("syntax error")
        assert str(err) == "syntax error"

    def test_cursorpos_attribute(self):
        err = PgQueryError("error", cursorpos=15)
        assert err.cursorpos == 15

    def test_optional_fields_default_to_none(self):
        err = PgQueryError("error")
        assert err.context is None
        assert err.funcname is None
        assert err.filename is None

    def test_all_fields_populated(self):
        err = PgQueryError(
            "error",
            cursorpos=5,
            context="some context",
            funcname="parse_func",
            filename="parser.c",
            lineno=42,
        )
        assert err.cursorpos == 5
        assert err.context == "some context"
        assert err.funcname == "parse_func"
        assert err.filename == "parser.c"
        assert err.lineno == 42

    def test_inherits_from_exception(self):
        err = PgQueryError("error")
        assert isinstance(err, Exception)

    def test_catchable(self):
        with pytest.raises(PgQueryError, match="bad sql"):
            raise PgQueryError("bad sql")


class _MockResult(Structure):
    """Minimal ctypes struct with an error pointer for testing check_error."""

    _fields_ = [
        ("error", POINTER(CPgQueryError)),
    ]


class TestCheckError:
    def test_null_error_does_not_raise(self):
        result = _MockResult()
        result.error = POINTER(CPgQueryError)()  # NULL pointer
        check_error(result)

    def test_non_null_error_raises(self):
        c_err = CPgQueryError()
        c_err.message = b'syntax error at or near "SELEC"'
        c_err.cursorpos = 1
        c_err.context = None
        c_err.funcname = b"parse"
        c_err.filename = b"parser.c"
        c_err.lineno = 100

        result = _MockResult()
        result.error = ctypes.pointer(c_err)

        with pytest.raises(PgQueryError, match="syntax error") as exc_info:
            check_error(result)

        assert exc_info.value.cursorpos == 1
        assert exc_info.value.context is None
        assert exc_info.value.funcname == "parse"

    def test_non_null_error_with_null_optional_fields(self):
        c_err = CPgQueryError()
        c_err.message = b"error"
        c_err.cursorpos = 0
        c_err.context = None
        c_err.funcname = None
        c_err.filename = None
        c_err.lineno = 0

        result = _MockResult()
        result.error = ctypes.pointer(c_err)

        with pytest.raises(PgQueryError) as exc_info:
            check_error(result)

        assert exc_info.value.context is None
        assert exc_info.value.funcname is None
        assert exc_info.value.filename is None
