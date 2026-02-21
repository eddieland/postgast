from postgast import normalize

from .conftest import assert_pg_query_error


class TestNormalize:
    def test_simple_constant(self):
        result = normalize("SELECT * FROM t WHERE id = 42")
        assert result == "SELECT * FROM t WHERE id = $1"

    def test_multiple_constants(self):
        result = normalize("SELECT * FROM t WHERE id = 42 AND name = 'foo'")
        assert "$1" in result
        assert "$2" in result
        assert "42" not in result
        assert "'foo'" not in result

    def test_no_constants(self):
        result = normalize("SELECT * FROM t")
        assert result == "SELECT * FROM t"

    def test_invalid_sql_raises_pg_query_error(self):
        assert_pg_query_error(normalize, "SELEC * FROM t", check_cursorpos=True)
