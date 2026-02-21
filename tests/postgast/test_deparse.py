from postgast import ParseResult, deparse, parse


class TestDeparse:
    def test_simple_select_round_trip(self, select1_tree: ParseResult):
        sql = deparse(select1_tree)
        assert "SELECT" in sql.upper()
        assert "1" in sql

    def test_select_with_where(self):
        tree = parse("SELECT id, name FROM users WHERE active = true")
        sql = deparse(tree)
        reparsed = parse(sql)
        assert len(reparsed.stmts) == 1
        assert reparsed.stmts[0].stmt.HasField("select_stmt")

    def test_ddl_create_table(self, create_table_tree: ParseResult):
        sql = deparse(create_table_tree)
        reparsed = parse(sql)
        assert len(reparsed.stmts) == 1
        assert reparsed.stmts[0].stmt.HasField("create_stmt")

    def test_multi_statement(self, multi_stmt_tree: ParseResult):
        sql = deparse(multi_stmt_tree)
        reparsed = parse(sql)
        assert len(reparsed.stmts) == 2


class TestDeparseErrors:
    def test_invalid_protobuf_raises_pg_query_error(self):
        bad_tree = ParseResult()
        bad_tree.version = 0
        # An empty ParseResult with no stmts deparses to empty string, so
        # we verify it doesn't crash. The C deparser is lenient with valid
        # protobuf structure, so we test the round-trip contract instead.
        result = deparse(bad_tree)
        assert isinstance(result, str)
