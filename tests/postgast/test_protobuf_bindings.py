class TestProtobufModule:
    def test_pg_query_pb2_importable(self):
        from postgast._pg_query_pb2 import ParseResult

        assert ParseResult is not None

    def test_parse_result_has_version_field(self):
        from postgast._pg_query_pb2 import ParseResult

        msg = ParseResult()
        assert hasattr(msg, "version")

    def test_parse_result_has_stmts_field(self):
        from postgast._pg_query_pb2 import ParseResult

        msg = ParseResult()
        assert hasattr(msg, "stmts")
        assert len(msg.stmts) == 0


class TestProtobufReExport:
    def test_pg_query_pb2_from_postgast(self):
        from postgast import pg_query_pb2

        assert hasattr(pg_query_pb2, "ParseResult")
        assert hasattr(pg_query_pb2, "Node")
        assert hasattr(pg_query_pb2, "SelectStmt")
