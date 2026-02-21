import pytest

from postgast import PgQueryError, normalize


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
        with pytest.raises(PgQueryError) as exc_info:
            normalize("SELEC * FROM t")
        assert exc_info.value.message
        assert exc_info.value.cursorpos > 0


class TestPublicImport:
    def test_normalize_importable(self):
        from postgast import normalize as n

        assert callable(n)

    def test_pg_query_error_importable(self):
        from postgast import PgQueryError as E

        assert issubclass(E, Exception)
