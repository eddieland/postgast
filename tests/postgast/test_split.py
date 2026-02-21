import pytest

from postgast import split

from .conftest import assert_pg_query_error


class TestSplit:
    """Tests for split() with default method (parser)."""

    def test_single_statement(self):
        result = split("SELECT 1")
        assert result == ["SELECT 1"]

    def test_two_statements(self):
        result = split("SELECT 1; SELECT 2")
        assert len(result) == 2
        assert "SELECT 1" in result[0]
        assert "SELECT 2" in result[1]

    def test_empty_string(self):
        result = split("")
        assert result == []

    def test_empty_semicolons_skipped(self):
        result = split("SELECT 1;;; SELECT 2")
        assert len(result) == 2

    def test_multibyte_utf8(self):
        result = split("SELECT '日本語'; SELECT 1")
        assert len(result) == 2
        assert "日本語" in result[0]
        assert "SELECT 1" in result[1]

    def test_whitespace_only(self):
        result = split("   ")
        assert result == []

    def test_statements_with_comments(self):
        result = split("SELECT 1;\n\n-- comment\nSELECT 2")
        assert len(result) == 2


class TestSplitParser:
    """Tests for split() with method='parser'."""

    def test_basic_splitting(self):
        result = split("SELECT 1; SELECT 2", method="parser")
        assert len(result) == 2
        assert "SELECT 1" in result[0]
        assert "SELECT 2" in result[1]

    def test_multibyte_characters(self):
        result = split("SELECT '日本語'; SELECT 1", method="parser")
        assert len(result) == 2
        assert "日本語" in result[0]
        assert "SELECT 1" in result[1]

    def test_empty_string(self):
        result = split("", method="parser")
        assert result == []

    def test_invalid_sql_raises_pg_query_error(self):
        assert_pg_query_error(lambda sql: split(sql, method="parser"), "SELECT '")

    def test_default_method_is_parser(self):
        """split() without method behaves identically to method='parser'."""
        sql = "SELECT 1; SELECT 2"
        assert split(sql) == split(sql, method="parser")


class TestSplitScanner:
    """Tests for split() with method='scanner' (existing behavior)."""

    def test_basic_splitting(self):
        result = split("SELECT 1; SELECT 2", method="scanner")
        assert len(result) == 2
        assert "SELECT 1" in result[0]
        assert "SELECT 2" in result[1]


class TestSplitErrors:
    def test_invalid_sql_raises_pg_query_error(self):
        assert_pg_query_error(split, "SELECT '")

    def test_invalid_method_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown split method"):
            split("SELECT 1", method="invalid")  # type: ignore[arg-type]
