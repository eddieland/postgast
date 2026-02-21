from postgast import split

from .conftest import assert_pg_query_error


class TestSplit:
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


class TestSplitErrors:
    def test_invalid_sql_raises_pg_query_error(self):
        assert_pg_query_error(split, "SELECT '")
