"""Boundary-condition tests — edge-case inputs at the Python/C boundary.

These tests are fast (small inputs) and should always run — no special marker.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import pytest

from postgast import PgQueryError, fingerprint, normalize, parse, scan, split

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# 3.1  Null-byte tests
# ---------------------------------------------------------------------------

_OPS: dict[str, Callable[..., Any]] = {
    "parse": parse,
    "normalize": normalize,
    "fingerprint": fingerprint,
    "split": split,
    "scan": scan,
}


class TestNullBytes:
    @pytest.mark.parametrize("name", _OPS)
    def test_embedded_null_byte(self, name: str) -> None:
        """Operation handles an embedded null byte without crashing."""
        with contextlib.suppress(PgQueryError):
            _OPS[name]("SELECT\x001")

    @pytest.mark.parametrize("name", _OPS)
    def test_leading_null_byte(self, name: str) -> None:
        with contextlib.suppress(PgQueryError):
            _OPS[name]("\x00SELECT 1")

    @pytest.mark.parametrize("name", _OPS)
    def test_trailing_null_byte(self, name: str) -> None:
        with contextlib.suppress(PgQueryError):
            _OPS[name]("SELECT 1\x00")


# ---------------------------------------------------------------------------
# 3.2  Control-character tests
# ---------------------------------------------------------------------------

_CONTROL_CHARS: list[tuple[str, str]] = [
    ("tab", "\t"),
    ("vertical_tab", "\v"),
    ("form_feed", "\f"),
    ("backspace", "\b"),
    ("bell", "\a"),
]


class TestControlCharacters:
    @pytest.mark.parametrize("char", [c for _, c in _CONTROL_CHARS], ids=[n for n, _ in _CONTROL_CHARS])
    def test_parse_with_control_char(self, char: str) -> None:
        with contextlib.suppress(PgQueryError):
            parse(f"SELECT{char}1")

    @pytest.mark.parametrize("char", [c for _, c in _CONTROL_CHARS], ids=[n for n, _ in _CONTROL_CHARS])
    def test_scan_with_control_char(self, char: str) -> None:
        with contextlib.suppress(PgQueryError):
            scan(f"SELECT{char}1")


# ---------------------------------------------------------------------------
# 3.3  Unicode edge-case tests
# ---------------------------------------------------------------------------


class TestUnicodeEdgeCases:
    def test_parse_emoji_string_literal(self) -> None:
        result = parse("SELECT '\U0001f389\U0001f680'")
        assert len(result.stmts) == 1

    def test_parse_zero_width_in_identifier(self) -> None:
        sql = 'SELECT "\u200bcol\u200d"'
        try:
            result = parse(sql)
            assert len(result.stmts) == 1
        except PgQueryError:
            pass

    def test_scan_non_bmp_codepoints(self) -> None:
        sql = "SELECT '\U0001f600\U0001f4a9'"
        try:
            result = scan(sql)
            assert len(result.tokens) > 0
        except PgQueryError:
            pass

    def test_split_multibyte_unicode(self) -> None:
        sql = "SELECT '\U0001f389'; SELECT '\u65e5\u672c\u8a9e'"
        try:
            result = split(sql)
            assert len(result) == 2
        except PgQueryError:
            pass


# ---------------------------------------------------------------------------
# 3.4  Malformed-SQL tests
# ---------------------------------------------------------------------------

_MALFORMED_PARSE_INPUTS: list[tuple[str, str]] = [
    ("unterminated_string", "SELECT 'unterminated"),
    ("unterminated_block_comment", "SELECT /* never closed"),
    ("mismatched_parens", "SELECT ((1)"),
    ("partial_insert", "INSERT INTO"),
    ("partial_create", "CREATE TABLE"),
]


class TestMalformedSQL:
    @pytest.mark.parametrize(
        "sql", [s for _, s in _MALFORMED_PARSE_INPUTS], ids=[n for n, _ in _MALFORMED_PARSE_INPUTS]
    )
    def test_parse_malformed(self, sql: str) -> None:
        with pytest.raises(PgQueryError):
            parse(sql)

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT 'unterminated",
            "SELECT ((1)",
        ],
        ids=["unterminated_string", "mismatched_parens"],
    )
    def test_normalize_malformed(self, sql: str) -> None:
        with pytest.raises(PgQueryError):
            normalize(sql)

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT 'unterminated",
            "SELECT ((1)",
        ],
        ids=["unterminated_string", "mismatched_parens"],
    )
    def test_fingerprint_malformed(self, sql: str) -> None:
        with pytest.raises(PgQueryError):
            fingerprint(sql)

    def test_split_unterminated_construct(self) -> None:
        with pytest.raises(PgQueryError):
            split("SELECT 'unterminated; SELECT 2")

    def test_scan_garbage_bytes(self) -> None:
        garbage = bytes(range(128, 256)).decode("latin-1")
        with contextlib.suppress(PgQueryError):
            scan(garbage)


# ---------------------------------------------------------------------------
# 3.5  Long-token tests
# ---------------------------------------------------------------------------


class TestLongTokens:
    def test_parse_long_identifier(self) -> None:
        ident = "a" * 100_000
        sql = f'SELECT "{ident}"'
        try:
            result = parse(sql)
            assert len(result.stmts) == 1
        except PgQueryError:
            pass

    def test_parse_long_string_literal(self) -> None:
        literal = "x" * 100_000
        sql = f"SELECT '{literal}'"
        try:
            result = parse(sql)
            assert len(result.stmts) == 1
        except PgQueryError:
            pass

    def test_scan_long_string_literal(self) -> None:
        literal = "x" * 100_000
        sql = f"SELECT '{literal}'"
        try:
            result = scan(sql)
            assert len(result.tokens) > 0
        except PgQueryError:
            pass


# ---------------------------------------------------------------------------
# 3.6  Error-resilience tests
# ---------------------------------------------------------------------------


class TestErrorResilience:
    def test_parse_succeeds_after_error(self) -> None:
        with pytest.raises(PgQueryError):
            parse("SELECT FROM")
        result = parse("SELECT 1")
        assert len(result.stmts) == 1

    def test_all_operations_succeed_after_errors(self) -> None:
        # Trigger an error in each operation, then verify it works after
        with pytest.raises(PgQueryError):
            parse("SELECT FROM")
        assert len(parse("SELECT 1").stmts) == 1

        with pytest.raises(PgQueryError):
            normalize("SELECT 'unterminated")
        assert isinstance(normalize("SELECT 1"), str)

        with pytest.raises(PgQueryError):
            fingerprint("SELECT 'unterminated")
        assert fingerprint("SELECT 1").hex

        with pytest.raises(PgQueryError):
            split("SELECT 'unterminated; SELECT 2")
        assert len(split("SELECT 1; SELECT 2")) == 2

        with pytest.raises(PgQueryError):
            scan("SELECT 'unterminated")
        assert len(scan("SELECT 1").tokens) > 0

    def test_error_success_loop_no_state_leakage(self) -> None:
        for i in range(100):
            with pytest.raises(PgQueryError):
                parse("SELECT FROM")
            result = parse("SELECT 1")
            assert len(result.stmts) == 1, f"Failed on cycle {i}"
