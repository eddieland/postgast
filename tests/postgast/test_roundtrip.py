"""Roundtrip tests: parse → deparse → re-parse equivalence."""

import pytest

from postgast import deparse, parse


def assert_roundtrip(sql: str) -> None:
    """Assert that the canonical form is stable after one roundtrip.

    Deparse canonicalizes SQL (e.g. ``INNER JOIN`` → ``JOIN``, ``integer`` → ``int``),
    so the deparsed text may differ from the original. We verify that the canonical
    form is a **fixed point**: deparsing the re-parsed canonical SQL produces the
    same string again.
    """
    canonical = deparse(parse(sql))
    canonical2 = deparse(parse(canonical))
    assert canonical == canonical2, (
        f"Canonical form not stable:\n  original:   {sql}\n  canonical:  {canonical}\n  canonical2: {canonical2}"
    )


# -- SELECT -------------------------------------------------------------------

SELECT_CASES = [
    "SELECT 1",
    "SELECT a, b, c FROM t",
    "SELECT * FROM t WHERE x = 1 AND y = 2",
    "SELECT a FROM t ORDER BY a DESC",
    "SELECT a FROM t LIMIT 10 OFFSET 5",
    "SELECT DISTINCT a, b FROM t",
    "SELECT a AS alias_a, b AS alias_b FROM t AS tbl",
    # Joins
    "SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id",
    "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id",
    "SELECT * FROM t1 RIGHT JOIN t2 ON t1.id = t2.id",
    "SELECT * FROM t1 FULL JOIN t2 ON t1.id = t2.id",
    "SELECT * FROM t1 CROSS JOIN t2",
    # Subqueries
    "SELECT * FROM (SELECT a FROM t) AS sub",
    "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t.id)",
    "SELECT * FROM t WHERE x IN (SELECT x FROM t2)",
    "SELECT (SELECT MAX(a) FROM t2) AS mx FROM t",
    # CTEs
    "WITH cte AS (SELECT a FROM t) SELECT * FROM cte",
    "WITH c1 AS (SELECT 1 AS x), c2 AS (SELECT 2 AS y) SELECT * FROM c1, c2",
    "WITH RECURSIVE r AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM r WHERE n < 10) SELECT * FROM r",
    # Window functions
    "SELECT ROW_NUMBER() OVER (ORDER BY a) FROM t",
    "SELECT SUM(x) OVER (PARTITION BY grp ORDER BY a) FROM t",
    "SELECT a, RANK() OVER w FROM t WINDOW w AS (ORDER BY a)",
    # Aggregates
    "SELECT COUNT(*) FROM t",
    "SELECT grp, SUM(x) FROM t GROUP BY grp",
    "SELECT grp, COUNT(*) FROM t GROUP BY grp HAVING COUNT(*) > 1",
]


class TestSelectRoundtrip:
    @pytest.mark.parametrize("sql", SELECT_CASES)
    def test_select_roundtrip(self, sql: str) -> None:
        assert_roundtrip(sql)


# -- DML ----------------------------------------------------------------------

DML_CASES = [
    # INSERT
    "INSERT INTO t (a, b) VALUES (1, 2)",
    "INSERT INTO t (a, b) VALUES (1, 2), (3, 4)",
    "INSERT INTO t (a) SELECT a FROM t2",
    "INSERT INTO t (a) VALUES (1) ON CONFLICT (a) DO NOTHING",
    "INSERT INTO t (a, b) VALUES (1, 2) ON CONFLICT (a) DO UPDATE SET b = EXCLUDED.b",
    # UPDATE
    "UPDATE t SET a = 1",
    "UPDATE t SET a = 1, b = 2 WHERE id = 3",
    "UPDATE t SET a = t2.a FROM t2 WHERE t.id = t2.id",
    "UPDATE t SET a = 1 RETURNING *",
    # DELETE
    "DELETE FROM t WHERE id = 1",
    "DELETE FROM t USING t2 WHERE t.id = t2.id",
    "DELETE FROM t WHERE id = 1 RETURNING *",
]


class TestDmlRoundtrip:
    @pytest.mark.parametrize("sql", DML_CASES)
    def test_dml_roundtrip(self, sql: str) -> None:
        assert_roundtrip(sql)


# -- DDL ----------------------------------------------------------------------

DDL_CASES = [
    # CREATE TABLE
    "CREATE TABLE t (id integer PRIMARY KEY, name text NOT NULL)",
    "CREATE TABLE t (id serial, val numeric DEFAULT 0)",
    "CREATE TABLE t (id integer, ref_id integer REFERENCES other(id))",
    "CREATE TABLE t (a integer, b integer, UNIQUE (a, b))",
    # ALTER TABLE
    "ALTER TABLE t ADD COLUMN c text",
    "ALTER TABLE t DROP COLUMN c",
    "ALTER TABLE t ADD CONSTRAINT u_a UNIQUE (a)",
    "ALTER TABLE t RENAME COLUMN a TO b",
    # CREATE INDEX
    "CREATE INDEX idx_a ON t (a)",
    "CREATE UNIQUE INDEX idx_u ON t (a, b)",
    "CREATE INDEX idx_lower ON t (lower(name))",
    # CREATE VIEW
    "CREATE VIEW v AS SELECT a, b FROM t",
    # CREATE OR REPLACE VIEW
    "CREATE OR REPLACE VIEW public.active_users AS SELECT id, name FROM users WHERE active",
    # DROP
    "DROP TABLE t",
    "DROP TABLE IF EXISTS t CASCADE",
    "DROP INDEX idx_a",
    "DROP VIEW v",
    # DROP FUNCTION / TRIGGER
    "DROP FUNCTION public.add(integer, integer)",
    "DROP TRIGGER my_trg ON public.my_table",
    # CREATE FUNCTION — simple SQL body
    "CREATE FUNCTION public.add(a integer, b integer) RETURNS integer LANGUAGE sql AS $$ SELECT a + b $$",
    # CREATE OR REPLACE FUNCTION
    "CREATE OR REPLACE FUNCTION public.add(a integer, b integer) RETURNS integer LANGUAGE sql AS $$ SELECT a + b $$",
    # PL/pgSQL trigger function with multi-line body
    """CREATE FUNCTION public.audit_fn() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO public.audit_log (table_name, action, row_data)
    VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW));
    RETURN NEW;
END;
$$""",
    # SECURITY DEFINER
    "CREATE OR REPLACE FUNCTION public.secure_fn() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$ BEGIN RETURN NEW; END; $$",
    # Default argument values
    "CREATE OR REPLACE FUNCTION public.greet(name text DEFAULT 'world'::text) RETURNS text LANGUAGE sql AS $$ SELECT 'Hello, ' || name $$",
    # Void return
    "CREATE OR REPLACE FUNCTION public.noop() RETURNS void LANGUAGE sql AS $$  $$",
    # Overloaded signatures (same name, different args) — tested individually
    "CREATE FUNCTION public.convert(val integer) RETURNS text LANGUAGE sql AS $$ SELECT val::text $$",
    "CREATE FUNCTION public.convert(val text) RETURNS text LANGUAGE sql AS $$ SELECT upper(val) $$",
    # CREATE TRIGGER — BEFORE INSERT
    "CREATE TRIGGER my_trg BEFORE INSERT ON public.my_table FOR EACH ROW EXECUTE FUNCTION public.my_fn()",
    # CREATE TRIGGER — AFTER INSERT
    "CREATE TRIGGER my_trg AFTER INSERT ON public.my_table FOR EACH ROW EXECUTE FUNCTION public.my_fn()",
    # CREATE TRIGGER — multi-event
    "CREATE TRIGGER my_trg AFTER INSERT OR UPDATE ON public.my_table FOR EACH ROW EXECUTE FUNCTION public.my_fn()",
    # CREATE OR REPLACE TRIGGER — multi-event
    "CREATE OR REPLACE TRIGGER my_trg AFTER INSERT OR UPDATE OR DELETE ON public.my_table FOR EACH ROW EXECUTE FUNCTION public.my_fn()",
    # CREATE PROCEDURE
    "CREATE PROCEDURE public.noop() LANGUAGE sql AS $$ SELECT 1 $$",
    # CREATE AGGREGATE
    "CREATE AGGREGATE public.my_sum(integer) (SFUNC = int4pl, STYPE = integer, INITCOND = '0')",
]


class TestDdlRoundtrip:
    @pytest.mark.parametrize("sql", DDL_CASES)
    def test_ddl_roundtrip(self, sql: str) -> None:
        assert_roundtrip(sql)


# -- Utility ------------------------------------------------------------------

UTILITY_CASES = [
    "EXPLAIN SELECT * FROM t",
    "EXPLAIN ANALYZE SELECT * FROM t",
    "SET search_path TO public",
    "GRANT SELECT ON t TO some_role",
    "REVOKE SELECT ON t FROM some_role",
]


class TestUtilityRoundtrip:
    @pytest.mark.parametrize("sql", UTILITY_CASES)
    def test_utility_roundtrip(self, sql: str) -> None:
        assert_roundtrip(sql)


# -- Edge cases ---------------------------------------------------------------

EDGE_CASES = [
    # Quoted identifiers
    'SELECT "MixedCase" FROM "MyTable"',
    'SELECT "select" FROM "from"',
    # Operator precedence
    "SELECT (a + b) * c FROM t",
    "SELECT NOT (x AND y) FROM t",
    "SELECT a OR b AND c FROM t",
    # NULL handling
    "SELECT * FROM t WHERE a IS NULL",
    "SELECT * FROM t WHERE a IS NOT NULL",
    "SELECT COALESCE(a, b, c) FROM t",
    "SELECT NULLIF(a, 0) FROM t",
    # CAST and type expressions
    "SELECT CAST(x AS integer) FROM t",
    "SELECT x::text FROM t",
    "SELECT '2024-01-01'::date",
]


class TestEdgeCaseRoundtrip:
    @pytest.mark.parametrize("sql", EDGE_CASES)
    def test_edge_case_roundtrip(self, sql: str) -> None:
        assert_roundtrip(sql)
