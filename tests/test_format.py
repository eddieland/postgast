"""Functional tests for format_sql: round-trip, idempotency, error handling."""

from __future__ import annotations

import pytest

from postgast import PgQueryError, deparse, format_sql, parse

# ── Round-trip: formatting preserves semantics ─────────────────────

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
    "SELECT * FROM a CROSS JOIN b",
    "SELECT * FROM (SELECT 1 AS x) AS sub",
    "WITH cte AS (SELECT 1) SELECT * FROM cte",
    "SELECT 1 UNION ALL SELECT 2",
    "SELECT 1 INTERSECT SELECT 2",
    "SELECT 1 EXCEPT SELECT 2",
    "INSERT INTO t (a) VALUES (1)",
    "INSERT INTO t SELECT * FROM s",
    "INSERT INTO t (a, b) VALUES (1, 2) ON CONFLICT (a) DO NOTHING",
    "INSERT INTO t (a, b) VALUES (1, 2) ON CONFLICT (a) DO UPDATE SET b = EXCLUDED.b",
    "INSERT INTO users (name) VALUES ('Bob') RETURNING id",
    "UPDATE t SET a = 1 WHERE b = 2",
    "UPDATE users SET name = 'bar' WHERE id = 1 RETURNING id, name",
    "DELETE FROM t WHERE a = 1",
    "DELETE FROM users WHERE id = 1 RETURNING id",
    "CREATE TABLE t (id integer PRIMARY KEY, name text NOT NULL)",
    "CREATE TABLE IF NOT EXISTS users (id integer)",
    "CREATE INDEX idx ON t (a)",
    "CREATE UNIQUE INDEX idx_email ON users (email)",
    "CREATE INDEX idx_active ON users (name) WHERE active = true",
    "CREATE VIEW v AS SELECT 1",
    "CREATE OR REPLACE VIEW v AS SELECT 1",
    "ALTER TABLE t ADD COLUMN x integer",
    "ALTER TABLE users DROP COLUMN age",
    "ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id)",
    "DROP TABLE t",
    "DROP TABLE IF EXISTS t CASCADE",
    "DROP INDEX idx_users_name",
    "DROP VIEW active_users",
    "SELECT CASE WHEN x = 1 THEN 'a' ELSE 'b' END FROM t",
    "SELECT COALESCE(a, b) FROM t",
    "SELECT GREATEST(a, b), LEAST(c, d) FROM t",
    "SELECT NULLIF(a, 0) FROM t",
    "SELECT * FROM t WHERE x IN (1, 2, 3)",
    "SELECT * FROM t WHERE x NOT IN (1, 2, 3)",
    "SELECT * FROM t WHERE name LIKE '%foo%'",
    "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM s WHERE s.id = t.id)",
    "SELECT * FROM t WHERE x BETWEEN 1 AND 10",
    "SELECT x::integer FROM t",
    "SELECT * FROM t WHERE x IS NULL",
    "SELECT * FROM t WHERE x IS NOT NULL",
    "SELECT * FROM t WHERE x IS TRUE",
    "SELECT * FROM t WHERE x IS NOT FALSE",
    "SELECT * FROM t WHERE NOT active",
    "SELECT ARRAY[1, 2, 3]",
    "SELECT * FROM t WHERE id = $1",
    "SELECT count(DISTINCT status) FROM orders",
    "SELECT row_number() OVER (PARTITION BY dept ORDER BY salary DESC) FROM employees",
    "SELECT public.users.id FROM public.users",
    "SELECT 3.14",
    "SELECT true, false",
    "SELECT 'hello'",
    "SELECT a + b FROM t",
    "SELECT * FROM t WHERE x <> 1",
    "(SELECT count(*) FROM t)",
]


@pytest.mark.parametrize("sql", ROUND_TRIP_CASES)
def test_round_trip(sql: str) -> None:
    """Formatted SQL parses to the same AST as the original."""
    formatted = format_sql(sql)
    assert deparse(parse(formatted)) == deparse(parse(sql)), f"Round-trip failed for: {sql}\nFormatted:\n{formatted}"


# ── Idempotency: formatting twice == formatting once ───────────────


@pytest.mark.parametrize("sql", ROUND_TRIP_CASES)
def test_idempotency(sql: str) -> None:
    once = format_sql(sql)
    twice = format_sql(once)
    assert twice == once, f"Not idempotent for: {sql}\nOnce:\n{once}\nTwice:\n{twice}"


# ── Error handling ─────────────────────────────────────────────────


def test_invalid_sql_raises() -> None:
    with pytest.raises(PgQueryError):
        format_sql("NOT VALID SQL ???")


# ── Fallback for unhandled statement types ─────────────────────────


def test_fallback_unhandled_statement() -> None:
    result = format_sql("LISTEN channel")
    assert deparse(parse(result)) == deparse(parse("LISTEN channel"))
    assert "channel" in result.lower()


def test_fallback_mixed_statements() -> None:
    result = format_sql("SELECT 1; LISTEN channel")
    assert "SELECT" in result
    assert "channel" in result.lower()
    assert len(parse(result).stmts) == 2


# ── format_sql accepts a ParseResult directly ─────────────────────


def test_format_accepts_parse_result() -> None:
    tree = parse("SELECT 1")
    assert format_sql(tree) == format_sql("SELECT 1")
