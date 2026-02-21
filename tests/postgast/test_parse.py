from postgast import parse

from .conftest import assert_pg_query_error


class TestParse:
    def test_simple_select(self, select1_tree):
        assert select1_tree.version > 0
        assert len(select1_tree.stmts) == 1
        assert select1_tree.stmts[0].stmt.HasField("select_stmt")

    def test_multi_statement(self, multi_stmt_tree):
        assert len(multi_stmt_tree.stmts) == 2

    def test_ddl_create_table(self, create_table_tree):
        assert len(create_table_tree.stmts) == 1
        assert create_table_tree.stmts[0].stmt.HasField("create_stmt")

    def test_invalid_sql_raises_pg_query_error(self):
        assert_pg_query_error(parse, "SELECT FROM", check_cursorpos=True)

    def test_empty_string_returns_empty_stmts(self):
        result = parse("")
        assert len(result.stmts) == 0
