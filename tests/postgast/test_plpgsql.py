from postgast import parse_plpgsql

from .conftest import assert_pg_query_error

# Simple PL/pgSQL function used across multiple tests.
SIMPLE_FUNC = """\
CREATE FUNCTION add(a int, b int) RETURNS int AS $$
BEGIN
    RETURN a + b;
END;
$$ LANGUAGE plpgsql;
"""

FUNC_WITH_DECLARE = """\
CREATE FUNCTION greet(name text) RETURNS text AS $$
DECLARE
    greeting text;
BEGIN
    greeting := 'Hello, ' || name;
    RETURN greeting;
END;
$$ LANGUAGE plpgsql;
"""

FUNC_WITH_IF = """\
CREATE FUNCTION abs_val(x int) RETURNS int AS $$
BEGIN
    IF x < 0 THEN
        RETURN -x;
    ELSE
        RETURN x;
    END IF;
END;
$$ LANGUAGE plpgsql;
"""

FUNC_WITH_SQL = """\
CREATE FUNCTION get_user_name(uid int) RETURNS text AS $$
DECLARE
    result text;
BEGIN
    SELECT name INTO result FROM users WHERE id = uid;
    RETURN result;
END;
$$ LANGUAGE plpgsql;
"""

FUNC_WITH_LOOP = """\
CREATE FUNCTION sum_to(n int) RETURNS int AS $$
DECLARE
    total int := 0;
    i int := 1;
BEGIN
    WHILE i <= n LOOP
        total := total + i;
        i := i + 1;
    END LOOP;
    RETURN total;
END;
$$ LANGUAGE plpgsql;
"""


class TestParsePlpgsql:
    def test_simple_function_returns_list(self):
        result = parse_plpgsql(SIMPLE_FUNC)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_simple_function_has_plpgsql_function_key(self):
        result = parse_plpgsql(SIMPLE_FUNC)
        func = result[0]
        assert "PLpgSQL_function" in func

    def test_function_with_declare(self):
        result = parse_plpgsql(FUNC_WITH_DECLARE)
        func = result[0]["PLpgSQL_function"]
        # The function should have datums (variable declarations)
        assert "datums" in func
        assert len(func["datums"]) > 0

    def test_function_with_if_else(self):
        result = parse_plpgsql(FUNC_WITH_IF)
        func = result[0]["PLpgSQL_function"]
        # Action body should contain statements
        action = func["action"]
        assert "PLpgSQL_stmt_block" in action
        body = action["PLpgSQL_stmt_block"]["body"]
        # At least one statement should be an IF
        stmt_types = [list(stmt.keys())[0] for stmt in body]
        assert "PLpgSQL_stmt_if" in stmt_types

    def test_function_with_sql_statements(self):
        result = parse_plpgsql(FUNC_WITH_SQL)
        func = result[0]["PLpgSQL_function"]
        assert "action" in func

    def test_function_with_loop(self):
        result = parse_plpgsql(FUNC_WITH_LOOP)
        func = result[0]["PLpgSQL_function"]
        action = func["action"]
        body = action["PLpgSQL_stmt_block"]["body"]
        stmt_types = [list(stmt.keys())[0] for stmt in body]
        assert "PLpgSQL_stmt_while" in stmt_types

    def test_function_with_parameters(self):
        result = parse_plpgsql(SIMPLE_FUNC)
        func = result[0]["PLpgSQL_function"]
        # Parameters show up as datums
        assert "datums" in func
        datum_types = [list(d.keys())[0] for d in func["datums"]]
        assert "PLpgSQL_var" in datum_types

    def test_create_or_replace(self):
        sql = SIMPLE_FUNC.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION")
        result = parse_plpgsql(sql)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "PLpgSQL_function" in result[0]

    def test_public_import(self):
        from postgast import parse_plpgsql as imported_func

        assert callable(imported_func)


class TestParsePlpgsqlErrors:
    def test_invalid_plpgsql_raises_error(self):
        sql = """\
CREATE FUNCTION bad() RETURNS void AS $$
BEGIN
    IF true THEN
    -- missing END IF
END;
$$ LANGUAGE plpgsql;
"""
        assert_pg_query_error(parse_plpgsql, sql)

    def test_non_plpgsql_function_returns_trivial_result(self):
        # libpg_query does not reject non-plpgsql functions — it returns a
        # near-empty structure.  We pass this through as-is for consistency
        # with the C library.  Users should only pass LANGUAGE plpgsql functions.
        sql = "CREATE FUNCTION f() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql;"
        result = parse_plpgsql(sql)
        assert isinstance(result, list)
        assert result == [{"PLpgSQL_function": {"datums": []}}]
