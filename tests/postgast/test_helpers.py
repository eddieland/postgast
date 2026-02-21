from __future__ import annotations

from postgast import extract_columns, extract_functions, extract_tables, find_nodes, parse


class TestFindNodes:
    def test_finds_matching_nodes(self):
        result = parse("SELECT * FROM users JOIN orders ON users.id = orders.user_id")
        nodes = list(find_nodes(result, "RangeVar"))
        assert len(nodes) == 2
        relnames = [n.relname for n in nodes]  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue,reportUnknownVariableType]
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
    def test_simple_table(self):
        result = parse("SELECT * FROM users")
        assert extract_tables(result) == ["users"]

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
        result = parse("SELECT name, age FROM users")
        assert extract_columns(result) == ["name", "age"]

    def test_table_qualified(self):
        result = parse("SELECT u.name FROM users u")
        assert extract_columns(result) == ["u.name"]

    def test_star(self):
        result = parse("SELECT * FROM users")
        assert extract_columns(result) == ["*"]

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
    def test_extract_tables_on_subtree(self):
        result = parse("SELECT * FROM users")
        select_stmt = result.stmts[0].stmt.select_stmt
        assert extract_tables(select_stmt) == ["users"]

    def test_extract_columns_on_subtree(self):
        result = parse("SELECT a, b FROM t")
        select_stmt = result.stmts[0].stmt.select_stmt
        assert extract_columns(select_stmt) == ["a", "b"]

    def test_extract_functions_on_subtree(self):
        result = parse("SELECT count(*) FROM t")
        select_stmt = result.stmts[0].stmt.select_stmt
        assert extract_functions(select_stmt) == ["count"]


class TestHelpersPublicImport:
    def test_import_all_helpers(self):
        from postgast import extract_columns as ec
        from postgast import extract_functions as ef
        from postgast import extract_tables as et
        from postgast import find_nodes as fn

        assert callable(fn)
        assert callable(et)
        assert callable(ec)
        assert callable(ef)
