"""Tests for SQL pretty-printer (format_sql)."""

from __future__ import annotations

import pytest

from postgast import PgQueryError, deparse, format_sql, parse


def _round_trip_ok(sql: str) -> bool:
    """Check that formatting preserves semantics via parse-deparse round-trip."""
    return deparse(parse(format_sql(sql))) == deparse(parse(sql))


# ── Expression formatting (task 2.10) ─────────────────────────────


class TestExpressions:
    def test_integer_literal(self) -> None:
        result = format_sql("SELECT 42")
        assert "42" in result
        assert _round_trip_ok("SELECT 42")

    def test_float_literal(self) -> None:
        assert _round_trip_ok("SELECT 3.14")

    def test_string_literal(self) -> None:
        result = format_sql("SELECT 'hello'")
        assert "'hello'" in result
        assert _round_trip_ok("SELECT 'hello'")

    def test_boolean_literal(self) -> None:
        result = format_sql("SELECT true, false")
        assert "TRUE" in result
        assert "FALSE" in result
        assert _round_trip_ok("SELECT true, false")

    def test_null_literal(self) -> None:
        result = format_sql("SELECT NULL")
        assert "NULL" in result
        assert _round_trip_ok("SELECT NULL")

    def test_column_ref_simple(self) -> None:
        assert _round_trip_ok("SELECT id FROM t")

    def test_column_ref_qualified(self) -> None:
        assert _round_trip_ok("SELECT t.id FROM t")

    def test_column_ref_star(self) -> None:
        assert _round_trip_ok("SELECT * FROM t")

    def test_binary_operator(self) -> None:
        assert _round_trip_ok("SELECT a + b FROM t")

    def test_comparison_operator(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE x = 1")
        assert _round_trip_ok("SELECT * FROM t WHERE x <> 1")
        assert _round_trip_ok("SELECT * FROM t WHERE x > 1")
        assert _round_trip_ok("SELECT * FROM t WHERE x < 1")

    def test_like(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE name LIKE '%foo%'")

    def test_between(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE x BETWEEN 1 AND 10")

    def test_in_list(self) -> None:
        result = format_sql("SELECT * FROM t WHERE x IN (1, 2, 3)")
        assert "IN" in result
        assert _round_trip_ok("SELECT * FROM t WHERE x IN (1, 2, 3)")

    def test_not_in_list(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE x NOT IN (1, 2, 3)")

    def test_is_null(self) -> None:
        result = format_sql("SELECT * FROM t WHERE x IS NULL")
        assert "IS NULL" in result
        assert _round_trip_ok("SELECT * FROM t WHERE x IS NULL")

    def test_is_not_null(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE x IS NOT NULL")

    def test_bool_and_or(self) -> None:
        sql = "SELECT * FROM t WHERE a = 1 AND b = 2 OR c = 3"
        assert "AND" in format_sql(sql)
        assert _round_trip_ok(sql)

    def test_not_expr(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE NOT active")

    def test_func_call(self) -> None:
        result = format_sql("SELECT count(*), sum(amount) FROM orders")
        assert "count(*)" in result
        assert "sum(amount)" in result
        assert _round_trip_ok("SELECT count(*), sum(amount) FROM orders")

    def test_func_call_distinct(self) -> None:
        assert _round_trip_ok("SELECT count(DISTINCT status) FROM orders")

    def test_type_cast(self) -> None:
        assert _round_trip_ok("SELECT x::integer FROM t")

    def test_case_expr(self) -> None:
        sql = "SELECT CASE WHEN x = 1 THEN 'a' WHEN x = 2 THEN 'b' ELSE 'c' END FROM t"
        result = format_sql(sql)
        assert "CASE" in result
        assert "WHEN" in result
        assert "THEN" in result
        assert "ELSE" in result
        assert "END" in result
        assert _round_trip_ok(sql)

    def test_sublink_exists(self) -> None:
        sql = "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM other WHERE other.id = t.id)"
        result = format_sql(sql)
        assert "EXISTS" in result
        assert _round_trip_ok(sql)

    def test_sublink_scalar(self) -> None:
        sql = "SELECT (SELECT count(*) FROM t) AS cnt"
        assert _round_trip_ok(sql)

    def test_coalesce(self) -> None:
        assert _round_trip_ok("SELECT COALESCE(a, b, c) FROM t")

    def test_greatest_least(self) -> None:
        assert _round_trip_ok("SELECT GREATEST(a, b), LEAST(c, d) FROM t")

    def test_nullif(self) -> None:
        assert _round_trip_ok("SELECT NULLIF(a, 0) FROM t")

    def test_param_ref(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE id = $1")

    def test_array_expr(self) -> None:
        assert _round_trip_ok("SELECT ARRAY[1, 2, 3]")

    def test_boolean_test(self) -> None:
        assert _round_trip_ok("SELECT * FROM t WHERE x IS TRUE")
        assert _round_trip_ok("SELECT * FROM t WHERE x IS NOT FALSE")


# ── SELECT formatting (task 3.8) ──────────────────────────────────


class TestSelectFormatting:
    def test_simple_select(self) -> None:
        result = format_sql("SELECT 1")
        assert result == "SELECT\n  1;"

    def test_multi_column(self) -> None:
        result = format_sql("SELECT a, b, c FROM t")
        assert "SELECT" in result
        assert "  a," in result
        assert "  b," in result
        assert "  c" in result
        assert _round_trip_ok("SELECT a, b, c FROM t")

    def test_select_star(self) -> None:
        assert _round_trip_ok("SELECT * FROM t")

    def test_select_distinct(self) -> None:
        result = format_sql("SELECT DISTINCT a, b FROM t")
        assert "SELECT DISTINCT" in result
        assert _round_trip_ok("SELECT DISTINCT a, b FROM t")

    def test_select_alias(self) -> None:
        result = format_sql("SELECT a AS x FROM t")
        assert "AS x" in result
        assert _round_trip_ok("SELECT a AS x FROM t")

    def test_from_clause(self) -> None:
        result = format_sql("SELECT * FROM users")
        assert "FROM" in result
        assert "  users" in result

    def test_from_with_schema(self) -> None:
        assert _round_trip_ok("SELECT * FROM public.users")

    def test_from_with_alias(self) -> None:
        result = format_sql("SELECT * FROM users u")
        assert "users u" in result

    def test_join(self) -> None:
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        result = format_sql(sql)
        assert "JOIN" in result
        assert "ON" in result
        assert _round_trip_ok(sql)

    def test_left_join(self) -> None:
        sql = "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id"
        result = format_sql(sql)
        assert "LEFT JOIN" in result
        assert _round_trip_ok(sql)

    def test_multiple_joins(self) -> None:
        sql = "SELECT * FROM a JOIN b ON a.id = b.a_id JOIN c ON b.id = c.b_id"
        result = format_sql(sql)
        assert result.count("JOIN") == 2
        assert _round_trip_ok(sql)

    def test_cross_join(self) -> None:
        assert _round_trip_ok("SELECT * FROM a CROSS JOIN b")

    def test_where_clause(self) -> None:
        result = format_sql("SELECT * FROM t WHERE x = 1")
        assert "WHERE" in result
        assert _round_trip_ok("SELECT * FROM t WHERE x = 1")

    def test_where_and(self) -> None:
        sql = "SELECT * FROM t WHERE a = 1 AND b = 2 AND c = 3"
        result = format_sql(sql)
        assert "AND" in result
        assert _round_trip_ok(sql)

    def test_group_by(self) -> None:
        sql = "SELECT dept, count(*) FROM employees GROUP BY dept"
        result = format_sql(sql)
        assert "GROUP BY" in result
        assert _round_trip_ok(sql)

    def test_group_by_having(self) -> None:
        sql = "SELECT dept, count(*) FROM employees GROUP BY dept HAVING count(*) > 5"
        result = format_sql(sql)
        assert "HAVING" in result
        assert _round_trip_ok(sql)

    def test_order_by(self) -> None:
        sql = "SELECT * FROM t ORDER BY a ASC, b DESC"
        result = format_sql(sql)
        assert "ORDER BY" in result
        assert "ASC" in result
        assert "DESC" in result
        assert _round_trip_ok(sql)

    def test_order_by_nulls(self) -> None:
        assert _round_trip_ok("SELECT * FROM t ORDER BY a NULLS FIRST, b NULLS LAST")

    def test_limit_offset(self) -> None:
        sql = "SELECT * FROM t LIMIT 10 OFFSET 20"
        result = format_sql(sql)
        assert "LIMIT" in result
        assert "OFFSET" in result
        assert _round_trip_ok(sql)

    def test_subquery_in_from(self) -> None:
        sql = "SELECT * FROM (SELECT id FROM users) AS sub"
        assert "AS sub" in format_sql(sql)
        assert _round_trip_ok(sql)

    def test_window_function(self) -> None:
        sql = "SELECT row_number() OVER (PARTITION BY dept ORDER BY salary DESC) FROM employees"
        assert _round_trip_ok(sql)

    def test_complex_select(self) -> None:
        sql = (
            "SELECT u.id, u.name, o.total "
            "FROM users u "
            "JOIN orders o ON u.id = o.user_id "
            "WHERE o.status = 'active' AND o.total > 100 "
            "GROUP BY u.id, u.name "
            "HAVING count(*) > 1 "
            "ORDER BY o.total DESC "
            "LIMIT 50"
        )
        result = format_sql(sql)
        for kw in ["SELECT", "FROM", "JOIN", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT"]:
            assert kw in result
        assert _round_trip_ok(sql)


# ── CTE and set operations (task 4.3) ─────────────────────────────


class TestCTEAndSetOps:
    def test_single_cte(self) -> None:
        sql = "WITH active AS (SELECT * FROM users WHERE active = true) SELECT * FROM active"
        result = format_sql(sql)
        assert "WITH" in result
        assert "active AS" in result
        assert _round_trip_ok(sql)

    def test_multiple_ctes(self) -> None:
        sql = "WITH a AS (SELECT 1 AS x), b AS (SELECT 2 AS y) SELECT * FROM a, b"
        assert _round_trip_ok(sql)

    def test_recursive_cte(self) -> None:
        sql = (
            "WITH RECURSIVE cnt AS (  SELECT 1 AS n   UNION ALL   SELECT n + 1 FROM cnt WHERE n < 10) SELECT n FROM cnt"
        )
        result = format_sql(sql)
        assert "RECURSIVE" in result
        assert _round_trip_ok(sql)

    def test_union(self) -> None:
        sql = "SELECT id FROM users UNION SELECT id FROM admins"
        result = format_sql(sql)
        assert "UNION" in result
        assert _round_trip_ok(sql)

    def test_union_all(self) -> None:
        sql = "SELECT id FROM users UNION ALL SELECT id FROM admins"
        result = format_sql(sql)
        assert "UNION ALL" in result
        assert _round_trip_ok(sql)

    def test_intersect(self) -> None:
        sql = "SELECT id FROM users INTERSECT SELECT id FROM admins"
        assert _round_trip_ok(sql)

    def test_except(self) -> None:
        sql = "SELECT id FROM users EXCEPT SELECT id FROM admins"
        assert _round_trip_ok(sql)


# ── DML formatting (task 5.4) ─────────────────────────────────────


class TestDMLFormatting:
    def test_insert_values(self) -> None:
        sql = "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')"
        result = format_sql(sql)
        assert "INSERT INTO" in result
        assert "VALUES" in result
        assert _round_trip_ok(sql)

    def test_insert_from_select(self) -> None:
        sql = "INSERT INTO archive SELECT * FROM users WHERE active = false"
        result = format_sql(sql)
        assert "INSERT INTO" in result
        assert "SELECT" in result
        assert _round_trip_ok(sql)

    def test_insert_on_conflict_nothing(self) -> None:
        sql = "INSERT INTO t (a, b) VALUES (1, 2) ON CONFLICT (a) DO NOTHING"
        result = format_sql(sql)
        assert "ON CONFLICT" in result
        assert "DO NOTHING" in result
        assert _round_trip_ok(sql)

    def test_insert_on_conflict_update(self) -> None:
        sql = "INSERT INTO t (a, b) VALUES (1, 2) ON CONFLICT (a) DO UPDATE SET b = EXCLUDED.b"
        assert _round_trip_ok(sql)

    def test_insert_returning(self) -> None:
        sql = "INSERT INTO users (name) VALUES ('Bob') RETURNING id"
        result = format_sql(sql)
        assert "RETURNING" in result
        assert _round_trip_ok(sql)

    def test_update(self) -> None:
        sql = "UPDATE users SET name = 'foo', active = false WHERE id = 1"
        result = format_sql(sql)
        assert "UPDATE" in result
        assert "SET" in result
        assert "WHERE" in result
        assert _round_trip_ok(sql)

    def test_update_returning(self) -> None:
        sql = "UPDATE users SET name = 'bar' WHERE id = 1 RETURNING id, name"
        result = format_sql(sql)
        assert "RETURNING" in result
        assert _round_trip_ok(sql)

    def test_delete(self) -> None:
        sql = "DELETE FROM users WHERE created_at < '2020-01-01'"
        result = format_sql(sql)
        assert "DELETE FROM" in result
        assert _round_trip_ok(sql)

    def test_delete_returning(self) -> None:
        sql = "DELETE FROM users WHERE id = 1 RETURNING id"
        assert _round_trip_ok(sql)

    def test_delete_using(self) -> None:
        sql = "DELETE FROM orders USING users WHERE orders.user_id = users.id AND users.active = false"
        result = format_sql(sql)
        assert "USING" in result
        assert _round_trip_ok(sql)


# ── DDL formatting (task 6.6) ─────────────────────────────────────


class TestDDLFormatting:
    def test_create_table(self) -> None:
        sql = "CREATE TABLE users (id serial PRIMARY KEY, name text NOT NULL, email text UNIQUE)"
        result = format_sql(sql)
        assert "CREATE TABLE" in result
        assert _round_trip_ok(sql)

    def test_create_table_if_not_exists(self) -> None:
        sql = "CREATE TABLE IF NOT EXISTS users (id integer)"
        result = format_sql(sql)
        assert "IF NOT EXISTS" in result
        assert _round_trip_ok(sql)

    def test_create_index(self) -> None:
        sql = "CREATE INDEX idx_users_name ON users (name)"
        result = format_sql(sql)
        assert "CREATE INDEX" in result
        assert _round_trip_ok(sql)

    def test_create_unique_index(self) -> None:
        sql = "CREATE UNIQUE INDEX idx_email ON users (email)"
        result = format_sql(sql)
        assert "UNIQUE" in result
        assert _round_trip_ok(sql)

    def test_create_index_where(self) -> None:
        sql = "CREATE INDEX idx_active ON users (name) WHERE active = true"
        assert _round_trip_ok(sql)

    def test_create_view(self) -> None:
        sql = "CREATE VIEW active_users AS SELECT * FROM users WHERE active = true"
        result = format_sql(sql)
        assert "CREATE" in result
        assert "VIEW" in result
        assert "AS" in result
        assert _round_trip_ok(sql)

    def test_create_or_replace_view(self) -> None:
        sql = "CREATE OR REPLACE VIEW v AS SELECT 1"
        result = format_sql(sql)
        assert "OR REPLACE" in result
        assert _round_trip_ok(sql)

    def test_alter_table_add_column(self) -> None:
        sql = "ALTER TABLE users ADD COLUMN age integer"
        result = format_sql(sql)
        assert "ALTER TABLE" in result
        assert "ADD COLUMN" in result
        assert _round_trip_ok(sql)

    def test_alter_table_drop_column(self) -> None:
        assert _round_trip_ok("ALTER TABLE users DROP COLUMN age")

    def test_alter_table_add_constraint(self) -> None:
        sql = "ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id)"
        assert _round_trip_ok(sql)

    def test_drop_table(self) -> None:
        sql = "DROP TABLE users"
        result = format_sql(sql)
        assert "DROP TABLE" in result
        assert _round_trip_ok(sql)

    def test_drop_if_exists_cascade(self) -> None:
        sql = "DROP TABLE IF EXISTS users CASCADE"
        result = format_sql(sql)
        assert "IF EXISTS" in result
        assert "CASCADE" in result
        assert _round_trip_ok(sql)

    def test_drop_index(self) -> None:
        assert _round_trip_ok("DROP INDEX idx_users_name")

    def test_drop_view(self) -> None:
        assert _round_trip_ok("DROP VIEW active_users")


# ── Multi-statement and integration (task 7.x) ────────────────────


class TestMultiStatement:
    def test_single_statement_semicolon(self) -> None:
        result = format_sql("SELECT 1")
        assert result.endswith(";")

    def test_multiple_statements(self) -> None:
        result = format_sql("SELECT 1; SELECT 2")
        assert ";\n\n" in result
        assert result.count(";") == 2


# ── Round-trip equivalence (task 7.2) ─────────────────────────────


ROUND_TRIP_CASES = [
    "SELECT 1",
    "SELECT a, b, c FROM t",
    "SELECT * FROM t WHERE x = 1",
    "SELECT * FROM t WHERE a = 1 AND b = 2",
    "SELECT * FROM t ORDER BY a DESC NULLS LAST",
    "SELECT * FROM t LIMIT 10 OFFSET 5",
    "SELECT DISTINCT a FROM t",
    "SELECT count(*) FROM t GROUP BY a HAVING count(*) > 1",
    "SELECT * FROM a JOIN b ON a.id = b.a_id",
    "SELECT * FROM a LEFT JOIN b ON a.id = b.a_id",
    "SELECT * FROM (SELECT 1 AS x) AS sub",
    "WITH cte AS (SELECT 1) SELECT * FROM cte",
    "SELECT 1 UNION ALL SELECT 2",
    "SELECT 1 INTERSECT SELECT 2",
    "INSERT INTO t (a) VALUES (1)",
    "INSERT INTO t SELECT * FROM s",
    "UPDATE t SET a = 1 WHERE b = 2",
    "DELETE FROM t WHERE a = 1",
    "CREATE TABLE t (id integer PRIMARY KEY, name text NOT NULL)",
    "CREATE INDEX idx ON t (a)",
    "CREATE VIEW v AS SELECT 1",
    "ALTER TABLE t ADD COLUMN x integer",
    "DROP TABLE t",
    "DROP TABLE IF EXISTS t CASCADE",
    "SELECT CASE WHEN x = 1 THEN 'a' ELSE 'b' END FROM t",
    "SELECT COALESCE(a, b) FROM t",
    "SELECT * FROM t WHERE x IN (1, 2, 3)",
    "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM s WHERE s.id = t.id)",
    "SELECT * FROM t WHERE x BETWEEN 1 AND 10",
    "SELECT x::integer FROM t",
    "SELECT * FROM t WHERE x IS NULL",
    "SELECT * FROM t WHERE x IS NOT NULL",
]


@pytest.mark.parametrize("sql", ROUND_TRIP_CASES)
def test_round_trip_equivalence(sql: str) -> None:
    formatted = format_sql(sql)
    assert deparse(parse(formatted)) == deparse(parse(sql)), f"Round-trip failed for: {sql}\nFormatted:\n{formatted}"


# ── Idempotency (task 7.3) ────────────────────────────────────────


@pytest.mark.parametrize("sql", ROUND_TRIP_CASES)
def test_idempotency(sql: str) -> None:
    once = format_sql(sql)
    twice = format_sql(once)
    assert twice == once, f"Not idempotent for: {sql}\nOnce:\n{once}\nTwice:\n{twice}"


# ── Error handling (task 7.4) ─────────────────────────────────────


def test_invalid_sql_raises() -> None:
    with pytest.raises(PgQueryError):
        format_sql("NOT VALID SQL ???")


# ── Fallback (task 7.5) ──────────────────────────────────────────


def test_fallback_unhandled_statement() -> None:
    result = format_sql("LISTEN channel")
    assert _round_trip_ok("LISTEN channel")
    assert "channel" in result.lower()


def test_fallback_mixed_statements() -> None:
    result = format_sql("SELECT 1; LISTEN channel")
    assert "SELECT" in result
    assert "channel" in result.lower()
    # Both statements should parse correctly
    parsed = parse(result)
    assert len(parsed.stmts) == 2


# ── Format accepts ParseResult (spec requirement) ────────────────


def test_format_accepts_parse_result() -> None:
    tree = parse("SELECT 1")
    result = format_sql(tree)
    assert result == format_sql("SELECT 1")
