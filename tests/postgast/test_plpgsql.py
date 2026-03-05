import contextlib
from pathlib import Path

import pytest

from postgast import PgQueryError, parse_plpgsql

from .conftest import assert_pg_query_error, load_yaml_cases

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


# -- YAML-driven error / edge-case data -------------------------------------

_CASES_DIR = Path(__file__).parent / "plpgsql_error_cases"
_YAML_CASES = load_yaml_cases(_CASES_DIR)
_ERROR_CASES = [(c["label"], c["sql"]) for c in _YAML_CASES if c["expect"] == "error"]
_NO_CRASH_CASES = [(c["label"], c["sql"]) for c in _YAML_CASES if c["expect"] == "no_crash"]

# Control characters cannot be represented in YAML, so they stay in Python.
_CONTROL_CHARS: list[tuple[str, str]] = [
    ("tab", "\t"),
    ("vertical_tab", "\v"),
    ("form_feed", "\f"),
    ("backspace", "\b"),
    ("bell", "\a"),
]


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

    # -- YAML-driven: malformed PL/pgSQL (must error) ------------------------

    @pytest.mark.parametrize("sql", [s for _, s in _ERROR_CASES], ids=[n for n, _ in _ERROR_CASES])
    def test_malformed_plpgsql_raises_error(self, sql: str) -> None:
        assert_pg_query_error(parse_plpgsql, sql)

    # -- YAML-driven: edge cases (must not crash) ----------------------------

    @pytest.mark.parametrize("sql", [s for _, s in _NO_CRASH_CASES], ids=[n for n, _ in _NO_CRASH_CASES])
    def test_edge_case_no_crash(self, sql: str) -> None:
        with contextlib.suppress(PgQueryError):
            parse_plpgsql(sql)

    # -- Error attribute verification ----------------------------------------

    def test_error_has_truthy_message(self) -> None:
        sql = """\
CREATE FUNCTION my_broken_func() RETURNS void AS $$
BEGIN
    IF true THEN
END;
$$ LANGUAGE plpgsql;"""
        with pytest.raises(PgQueryError) as exc_info:
            parse_plpgsql(sql)
        err = exc_info.value
        assert err.message
        # PL/pgSQL errors typically include context about which function was compiled
        if err.context is not None:
            assert "my_broken_func" in err.context

    # -- Error resilience ----------------------------------------------------

    def test_parse_plpgsql_succeeds_after_error(self) -> None:
        bad_sql = """\
CREATE FUNCTION f() RETURNS void AS $$
BEGIN
    IF true THEN
END;
$$ LANGUAGE plpgsql;"""
        with pytest.raises(PgQueryError):
            parse_plpgsql(bad_sql)
        # Must still work after error — no leaked C state
        result = parse_plpgsql(SIMPLE_FUNC)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "PLpgSQL_function" in result[0]

    # -- Null bytes (cannot represent in YAML) -------------------------------

    def test_embedded_null_byte(self) -> None:
        sql = SIMPLE_FUNC.replace("RETURN", "RETURN\x00")
        with contextlib.suppress(PgQueryError):
            parse_plpgsql(sql)

    def test_leading_null_byte(self) -> None:
        with contextlib.suppress(PgQueryError):
            parse_plpgsql("\x00" + SIMPLE_FUNC)

    def test_trailing_null_byte(self) -> None:
        with contextlib.suppress(PgQueryError):
            parse_plpgsql(SIMPLE_FUNC + "\x00")

    # -- Control characters (cannot represent in YAML) -----------------------

    @pytest.mark.parametrize("char", [c for _, c in _CONTROL_CHARS], ids=[n for n, _ in _CONTROL_CHARS])
    def test_control_char_in_body_no_crash(self, char: str) -> None:
        sql = f"""\
CREATE FUNCTION f() RETURNS void AS $$
BEGIN
    RETURN;{char}
END;
$$ LANGUAGE plpgsql;"""
        with contextlib.suppress(PgQueryError):
            parse_plpgsql(sql)
