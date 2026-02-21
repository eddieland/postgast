import pytest

from postgast import PgQueryError, pg_query_pb2, scan


class TestScan:
    def test_simple_select(self):
        result = scan("SELECT 1")
        assert result.version > 0
        assert len(result.tokens) == 2
        # SELECT is a reserved keyword
        select_tok = result.tokens[0]
        assert select_tok.token == pg_query_pb2.SELECT
        assert select_tok.keyword_kind == pg_query_pb2.RESERVED_KEYWORD
        # 1 is an integer constant
        int_tok = result.tokens[1]
        assert int_tok.token == pg_query_pb2.ICONST
        assert int_tok.keyword_kind == pg_query_pb2.NO_KEYWORD

    def test_token_byte_positions(self):
        result = scan("SELECT 1")
        select_tok = result.tokens[0]
        assert select_tok.start == 0
        assert select_tok.end == 6
        int_tok = result.tokens[1]
        assert int_tok.start == 7
        assert int_tok.end == 8

    def test_keyword_classification(self):
        result = scan("SELECT * FROM t")
        tokens_by_name = {pg_query_pb2.Token.Name(t.token): t for t in result.tokens}
        assert tokens_by_name["SELECT"].keyword_kind == pg_query_pb2.RESERVED_KEYWORD
        assert tokens_by_name["FROM"].keyword_kind == pg_query_pb2.RESERVED_KEYWORD

    def test_operator(self):
        result = scan("SELECT 1 + 2")
        plus_tok = [t for t in result.tokens if t.token == pg_query_pb2.ASCII_43]
        assert len(plus_tok) == 1

    def test_string_literal(self):
        result = scan("SELECT 'hello'")
        str_tok = [t for t in result.tokens if t.token == pg_query_pb2.SCONST]
        assert len(str_tok) == 1

    def test_comment(self):
        result = scan("SELECT 1 -- comment")
        comment_tok = [t for t in result.tokens if t.token == pg_query_pb2.SQL_COMMENT]
        assert len(comment_tok) == 1

    def test_multibyte_utf8(self):
        sql = "SELECT 'café'"
        result = scan(sql)
        # Should tokenize without error; positions are byte offsets
        str_tok = [t for t in result.tokens if t.token == pg_query_pb2.SCONST][0]
        encoded = sql.encode("utf-8")
        extracted = encoded[str_tok.start : str_tok.end]
        assert "café".encode() in extracted

    def test_empty_string(self):
        result = scan("")
        assert len(result.tokens) == 0


class TestScanErrors:
    def test_unterminated_string_raises_error(self):
        with pytest.raises(PgQueryError) as exc_info:
            scan("SELECT 'unterminated")
        assert exc_info.value.message


class TestScanPublicImport:
    def test_scan_importable(self):
        from postgast import scan as s

        assert callable(s)
