from postgast import fingerprint

from .conftest import assert_pg_query_error


class TestFingerprint:
    def test_simple_fingerprint(self):
        result = fingerprint("SELECT 1")
        assert result.fingerprint != 0
        assert isinstance(result.fingerprint, int)
        assert len(result.hex) > 0
        assert isinstance(result.hex, str)

    def test_equivalent_queries_match(self):
        r1 = fingerprint("SELECT * FROM t WHERE id = 1")
        r2 = fingerprint("SELECT * FROM t WHERE id = 2")
        assert r1.fingerprint == r2.fingerprint
        assert r1.hex == r2.hex

    def test_different_queries_differ(self):
        r1 = fingerprint("SELECT 1")
        r2 = fingerprint("SELECT * FROM t")
        assert r1.fingerprint != r2.fingerprint

    def test_invalid_sql_raises_pg_query_error(self):
        assert_pg_query_error(fingerprint, "SELEC * FROM t")


class TestFingerprintResult:
    def test_named_tuple_unpacking(self):
        fp, hex_str = fingerprint("SELECT 1")
        assert isinstance(fp, int)
        assert isinstance(hex_str, str)

    def test_named_field_access(self):
        result = fingerprint("SELECT 1")
        assert isinstance(result.fingerprint, int)
        assert isinstance(result.hex, str)
