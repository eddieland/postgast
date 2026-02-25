from __future__ import annotations

from postgast import StatementInfo, classify_statement, parse


class TestDML:
    def test_select(self):
        info = classify_statement(parse("SELECT 1"))
        assert info == StatementInfo(action="SELECT", object_type=None, node_name="select_stmt")

    def test_insert(self):
        info = classify_statement(parse("INSERT INTO t VALUES (1)"))
        assert info is not None
        assert info.action == "INSERT"

    def test_update(self):
        info = classify_statement(parse("UPDATE t SET col = 1"))
        assert info is not None
        assert info.action == "UPDATE"

    def test_delete(self):
        info = classify_statement(parse("DELETE FROM t"))
        assert info is not None
        assert info.action == "DELETE"


class TestCreateDDL:
    def test_create_table(self):
        info = classify_statement(parse("CREATE TABLE t (id int)"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "TABLE"

    def test_create_view(self):
        info = classify_statement(parse("CREATE VIEW v AS SELECT 1"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "VIEW"

    def test_create_index(self):
        info = classify_statement(parse("CREATE INDEX idx ON t (col)"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "INDEX"

    def test_create_function(self):
        info = classify_statement(parse("CREATE FUNCTION f() RETURNS void LANGUAGE sql AS $$ $$"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "FUNCTION"

    def test_create_procedure(self):
        info = classify_statement(parse("CREATE PROCEDURE p() LANGUAGE sql AS $$ SELECT 1 $$"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "PROCEDURE"

    def test_create_trigger(self):
        info = classify_statement(parse("CREATE TRIGGER trg BEFORE INSERT ON t FOR EACH ROW EXECUTE FUNCTION f()"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "TRIGGER"

    def test_create_sequence(self):
        info = classify_statement(parse("CREATE SEQUENCE my_seq"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "SEQUENCE"

    def test_create_schema(self):
        info = classify_statement(parse("CREATE SCHEMA myschema"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "SCHEMA"

    def test_create_enum_type(self):
        info = classify_statement(parse("CREATE TYPE status AS ENUM ('a', 'b')"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "TYPE"

    def test_create_extension(self):
        info = classify_statement(parse("CREATE EXTENSION hstore"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "EXTENSION"

    def test_create_materialized_view(self):
        info = classify_statement(parse("CREATE MATERIALIZED VIEW mv AS SELECT 1"))
        assert info is not None
        assert info.action == "CREATE"
        assert info.object_type == "MATERIALIZED VIEW"


class TestAlterDDL:
    def test_alter_table(self):
        info = classify_statement(parse("ALTER TABLE t ADD COLUMN c int"))
        assert info is not None
        assert info.action == "ALTER"
        assert info.object_type == "TABLE"

    def test_alter_sequence(self):
        info = classify_statement(parse("ALTER SEQUENCE my_seq RESTART WITH 1"))
        assert info is not None
        assert info.action == "ALTER"
        assert info.object_type == "SEQUENCE"


class TestDropDDL:
    def test_drop_table(self):
        info = classify_statement(parse("DROP TABLE t"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "TABLE"

    def test_drop_view(self):
        info = classify_statement(parse("DROP VIEW v"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "VIEW"

    def test_drop_index(self):
        info = classify_statement(parse("DROP INDEX idx"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "INDEX"

    def test_drop_function(self):
        info = classify_statement(parse("DROP FUNCTION f()"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "FUNCTION"

    def test_drop_schema(self):
        info = classify_statement(parse("DROP SCHEMA myschema"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "SCHEMA"

    def test_drop_type(self):
        info = classify_statement(parse("DROP TYPE my_type"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "TYPE"

    def test_drop_sequence(self):
        info = classify_statement(parse("DROP SEQUENCE my_seq"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "SEQUENCE"

    def test_drop_materialized_view(self):
        info = classify_statement(parse("DROP MATERIALIZED VIEW mv"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "MATERIALIZED VIEW"

    def test_drop_database(self):
        info = classify_statement(parse("DROP DATABASE mydb"))
        assert info is not None
        assert info.action == "DROP"
        assert info.object_type == "DATABASE"


class TestGrantRevoke:
    def test_grant(self):
        info = classify_statement(parse("GRANT SELECT ON t TO role1"))
        assert info is not None
        assert info.action == "GRANT"

    def test_revoke(self):
        info = classify_statement(parse("REVOKE SELECT ON t FROM role1"))
        assert info is not None
        assert info.action == "REVOKE"


class TestOther:
    def test_truncate(self):
        info = classify_statement(parse("TRUNCATE t"))
        assert info is not None
        assert info.action == "TRUNCATE"
        assert info.object_type == "TABLE"

    def test_explain(self):
        info = classify_statement(parse("EXPLAIN SELECT 1"))
        assert info is not None
        assert info.action == "EXPLAIN"

    def test_refresh_materialized_view(self):
        info = classify_statement(parse("REFRESH MATERIALIZED VIEW mv"))
        assert info is not None
        assert info.action == "REFRESH"
        assert info.object_type == "MATERIALIZED VIEW"


class TestEdgeCases:
    def test_empty_tree(self):
        from postgast.pg_query_pb2 import ParseResult

        assert classify_statement(ParseResult()) is None

    def test_multi_statement_returns_first(self):
        info = classify_statement(parse("SELECT 1; INSERT INTO t VALUES (1)"))
        assert info is not None
        assert info.action == "SELECT"

    def test_tuple_unpacking(self):
        info = classify_statement(parse("CREATE TABLE t (id int)"))
        assert info is not None
        action, obj_type, node_name = info
        assert action == "CREATE"
        assert obj_type == "TABLE"
        assert node_name == "create_stmt"

    def test_node_name_field(self):
        info = classify_statement(parse("CREATE INDEX idx ON t (col)"))
        assert info is not None
        assert info.node_name == "index_stmt"
