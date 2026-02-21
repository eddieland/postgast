from __future__ import annotations

import pytest

from postgast import (
    FunctionIdentity,
    ParseResult,
    TriggerIdentity,
    ensure_or_replace,
    extract_columns,
    extract_function_identity,
    extract_functions,
    extract_tables,
    extract_trigger_identity,
    find_nodes,
    parse,
    set_or_replace,
)
from postgast._errors import PgQueryError


class TestFindNodes:
    def test_finds_matching_nodes(self):
        result = parse("SELECT * FROM users JOIN orders ON users.id = orders.user_id")
        nodes = list(find_nodes(result, "RangeVar"))
        assert len(nodes) == 2
        from postgast._pg_query_pb2 import RangeVar

        relnames = [n.relname for n in nodes if isinstance(n, RangeVar)]
        assert relnames == ["users", "orders"]

    def test_empty_result_for_no_matches(self):
        result = parse("SELECT 1")
        nodes = list(find_nodes(result, "RangeVar"))
        assert nodes == []

    def test_works_on_subtrees(self):
        result = parse("SELECT a, b FROM t")
        select_stmt = result.stmts[0].stmt.select_stmt
        nodes = list(find_nodes(select_stmt, "ColumnRef"))
        assert len(nodes) == 2

    def test_lazy_evaluation(self):
        result = parse("SELECT a, b, c FROM t")
        gen = find_nodes(result, "ColumnRef")
        first = next(gen)
        assert type(first).DESCRIPTOR.name == "ColumnRef"
        # Generator is not exhausted — remaining items still available
        remaining = list(gen)
        assert len(remaining) >= 1


class TestExtractTables:
    def test_simple_table(self, users_tree: ParseResult):
        assert extract_tables(users_tree) == ["users"]

    def test_schema_qualified(self):
        result = parse("SELECT * FROM public.users")
        assert extract_tables(result) == ["public.users"]

    def test_joins(self):
        result = parse("SELECT * FROM orders JOIN customers ON orders.id = customers.order_id")
        assert extract_tables(result) == ["orders", "customers"]

    def test_subquery(self):
        result = parse("SELECT * FROM (SELECT * FROM users) AS sub")
        assert extract_tables(result) == ["users"]

    def test_dml_targets(self):
        result = parse("INSERT INTO logs SELECT * FROM events")
        assert extract_tables(result) == ["logs", "events"]

    def test_duplicate_references(self):
        result = parse("SELECT * FROM t1 JOIN t1 ON t1.a = t1.b")
        assert extract_tables(result) == ["t1", "t1"]


class TestExtractColumns:
    def test_simple_columns(self):
        assert extract_columns(parse("SELECT name, age FROM users")) == ["name", "age"]

    def test_table_qualified(self):
        result = parse("SELECT u.name FROM users u")
        assert extract_columns(result) == ["u.name"]

    def test_star(self, users_tree: ParseResult):
        assert extract_columns(users_tree) == ["*"]

    def test_qualified_star(self):
        result = parse("SELECT u.* FROM users u")
        assert extract_columns(result) == ["u.*"]

    def test_where_clause_columns(self):
        result = parse("SELECT name FROM users WHERE age > 18")
        columns = extract_columns(result)
        assert "name" in columns
        assert "age" in columns


class TestExtractFunctions:
    def test_simple_call(self):
        result = parse("SELECT count(*) FROM users")
        assert extract_functions(result) == ["count"]

    def test_multiple_calls(self):
        result = parse("SELECT lower(name), upper(city) FROM users")
        assert extract_functions(result) == ["lower", "upper"]

    def test_schema_qualified(self):
        result = parse("SELECT pg_catalog.now()")
        assert extract_functions(result) == ["pg_catalog.now"]

    def test_nested_calls(self):
        result = parse("SELECT upper(lower(name)) FROM users")
        funcs = extract_functions(result)
        assert "upper" in funcs
        assert "lower" in funcs


class TestHelpersOnSubtree:
    def test_extract_tables_on_subtree(self, users_tree: ParseResult):
        select_stmt = users_tree.stmts[0].stmt.select_stmt
        assert extract_tables(select_stmt) == ["users"]

    def test_extract_columns_on_subtree(self):
        result = parse("SELECT a, b FROM t")
        select_stmt = result.stmts[0].stmt.select_stmt
        assert extract_columns(select_stmt) == ["a", "b"]

    def test_extract_functions_on_subtree(self):
        result = parse("SELECT count(*) FROM t")
        select_stmt = result.stmts[0].stmt.select_stmt
        assert extract_functions(select_stmt) == ["count"]


class TestSetOrReplace:
    def test_create_function(self):
        tree = parse("CREATE FUNCTION add(a int, b int) RETURNS int LANGUAGE sql AS $$ SELECT a + b $$")
        assert set_or_replace(tree) == 1
        # Verify the flag was actually set on the AST node
        from postgast import walk

        for _field, node in walk(tree):
            if type(node).DESCRIPTOR.name == "CreateFunctionStmt":
                from postgast._pg_query_pb2 import CreateFunctionStmt

                assert isinstance(node, CreateFunctionStmt)
                assert node.replace is True

    def test_create_procedure(self):
        tree = parse("CREATE PROCEDURE do_nothing() LANGUAGE sql AS $$ SELECT 1 $$")
        assert set_or_replace(tree) == 1

    def test_create_trigger(self):
        tree = parse("CREATE TRIGGER my_trig BEFORE INSERT ON t FOR EACH ROW EXECUTE FUNCTION fn()")
        assert set_or_replace(tree) == 1

    def test_create_view(self):
        tree = parse("CREATE VIEW v AS SELECT 1")
        assert set_or_replace(tree) == 1

    def test_already_or_replace(self):
        tree = parse("CREATE OR REPLACE FUNCTION add(a int, b int) RETURNS int LANGUAGE sql AS $$ SELECT a + b $$")
        assert set_or_replace(tree) == 0

    def test_no_eligible_stmts(self):
        tree = parse("SELECT 1; CREATE TABLE t (id int)")
        assert set_or_replace(tree) == 0

    def test_multi_statement(self):
        sql = "CREATE FUNCTION f1() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$; CREATE VIEW v AS SELECT 1"
        tree = parse(sql)
        assert set_or_replace(tree) == 2

    def test_mixed_statements(self):
        sql = "CREATE TABLE t (id int); CREATE FUNCTION f1() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$; SELECT 1"
        tree = parse(sql)
        assert set_or_replace(tree) == 1


class TestEnsureOrReplace:
    def test_function(self):
        result = ensure_or_replace("CREATE FUNCTION f() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$")
        assert "OR REPLACE" in result

    def test_procedure(self):
        result = ensure_or_replace("CREATE PROCEDURE p() LANGUAGE sql AS $$ SELECT 1 $$")
        assert "OR REPLACE" in result

    def test_trigger(self):
        result = ensure_or_replace("CREATE TRIGGER t BEFORE INSERT ON tbl FOR EACH ROW EXECUTE FUNCTION fn()")
        assert "OR REPLACE" in result

    def test_view(self):
        result = ensure_or_replace("CREATE VIEW v AS SELECT 1")
        assert "OR REPLACE" in result

    def test_idempotency(self):
        sql = "CREATE FUNCTION f() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$"
        first = ensure_or_replace(sql)
        second = ensure_or_replace(first)
        assert first == second

    def test_invalid_sql_raises(self):
        with pytest.raises(PgQueryError):
            ensure_or_replace("NOT VALID SQL !!!")


class TestExtractFunctionIdentity:
    def test_schema_qualified(self):
        tree = parse(
            "CREATE FUNCTION public.add(a integer, b integer) RETURNS integer AS $$ SELECT a + b $$ LANGUAGE sql"
        )
        result = extract_function_identity(tree)
        assert result == FunctionIdentity(schema="public", name="add")

    def test_unqualified(self):
        tree = parse("CREATE FUNCTION my_func() RETURNS void AS $$ $$ LANGUAGE sql")
        result = extract_function_identity(tree)
        assert result == FunctionIdentity(schema=None, name="my_func")

    def test_or_replace(self):
        tree = parse("CREATE OR REPLACE FUNCTION myschema.do_stuff() RETURNS void AS $$ $$ LANGUAGE sql")
        result = extract_function_identity(tree)
        assert result == FunctionIdentity(schema="myschema", name="do_stuff")

    def test_procedure_skipped(self):
        tree = parse("CREATE PROCEDURE public.my_proc() LANGUAGE sql AS $$ $$ ")
        assert extract_function_identity(tree) is None

    def test_no_match(self):
        tree = parse("SELECT 1")
        assert extract_function_identity(tree) is None

    def test_comments_before_name(self):
        tree = parse(
            "CREATE FUNCTION /* comment */ public.add(a int, b int) RETURNS int AS $$ SELECT a + b $$ LANGUAGE sql"
        )
        result = extract_function_identity(tree)
        assert result == FunctionIdentity(schema="public", name="add")


class TestExtractTriggerIdentity:
    def test_schema_qualified_table(self):
        tree = parse("CREATE TRIGGER my_trg AFTER INSERT ON public.orders FOR EACH ROW EXECUTE FUNCTION notify()")
        result = extract_trigger_identity(tree)
        assert result == TriggerIdentity(trigger="my_trg", schema="public", table="orders")

    def test_unqualified_table(self):
        tree = parse("CREATE TRIGGER audit_trg BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION audit()")
        result = extract_trigger_identity(tree)
        assert result == TriggerIdentity(trigger="audit_trg", schema=None, table="users")

    def test_or_replace(self):
        tree = parse(
            "CREATE OR REPLACE TRIGGER my_trg AFTER INSERT ON myschema.events FOR EACH ROW EXECUTE FUNCTION log_event()"
        )
        result = extract_trigger_identity(tree)
        assert result == TriggerIdentity(trigger="my_trg", schema="myschema", table="events")

    def test_no_match(self):
        tree = parse("SELECT 1")
        assert extract_trigger_identity(tree) is None


class TestIdentityTupleUnpacking:
    def test_unpack_function_identity(self):
        tree = parse("CREATE FUNCTION public.add() RETURNS void AS $$ $$ LANGUAGE sql")
        result = extract_function_identity(tree)
        assert result is not None
        schema, name = result
        assert schema == "public"
        assert name == "add"

    def test_unpack_trigger_identity(self):
        tree = parse("CREATE TRIGGER t AFTER INSERT ON public.orders FOR EACH ROW EXECUTE FUNCTION f()")
        result = extract_trigger_identity(tree)
        assert result is not None
        trigger, schema, table = result
        assert trigger == "t"
        assert schema == "public"
        assert table == "orders"
