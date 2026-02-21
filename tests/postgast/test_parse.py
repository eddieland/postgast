import pytest

from postgast import PgQueryError, parse


class TestParse:
    def test_simple_select(self):
        result = parse("SELECT 1")
        assert result.version > 0
        assert len(result.stmts) == 1
        assert result.stmts[0].stmt.HasField("select_stmt")

    def test_multi_statement(self):
        result = parse("SELECT 1; SELECT 2")
        assert len(result.stmts) == 2

    def test_ddl_create_table(self):
        result = parse("CREATE TABLE t (id int PRIMARY KEY, name text)")
        assert len(result.stmts) == 1
        assert result.stmts[0].stmt.HasField("create_stmt")

    def test_invalid_sql_raises_pg_query_error(self):
        with pytest.raises(PgQueryError) as exc_info:
            parse("SELECT FROM")
        assert exc_info.value.message
        assert exc_info.value.cursorpos > 0

    def test_empty_string_returns_empty_stmts(self):
        result = parse("")
        assert len(result.stmts) == 0


class TestParsePublicImport:
    def test_parse_importable(self):
        from postgast import parse as p

        assert callable(p)
