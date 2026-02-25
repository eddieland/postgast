from __future__ import annotations

import pytest

from postgast import to_drop
from postgast.errors import PgQueryError


class TestDropFunction:
    def test_named_params(self):
        sql = "CREATE FUNCTION public.add(a integer, b integer) RETURNS integer LANGUAGE sql AS $$ SELECT a + b $$"
        assert to_drop(sql) == "DROP FUNCTION public.add(int, int)"

    def test_no_arg(self):
        sql = "CREATE FUNCTION do_stuff() RETURNS void LANGUAGE sql AS $$ SELECT 1 $$"
        assert to_drop(sql) == "DROP FUNCTION do_stuff()"

    def test_out_exclusion(self):
        sql = (
            "CREATE FUNCTION get_pair(IN x int, OUT a int, OUT b int) RETURNS RECORD LANGUAGE sql AS $$ SELECT 1, 2 $$"
        )
        assert to_drop(sql) == "DROP FUNCTION get_pair(int)"

    def test_variadic(self):
        sql = "CREATE FUNCTION concat_all(VARIADIC items text[]) RETURNS text LANGUAGE sql AS $$ SELECT array_to_string(items, ',') $$"
        assert to_drop(sql) == "DROP FUNCTION concat_all(text[])"

    def test_unqualified(self):
        sql = "CREATE FUNCTION myfunc(x int) RETURNS int LANGUAGE sql AS $$ SELECT x $$"
        assert to_drop(sql) == "DROP FUNCTION myfunc(int)"

    def test_quoted_identifiers(self):
        sql = 'CREATE FUNCTION "My Schema"."My Func"("My Param" integer) RETURNS integer LANGUAGE sql AS $$ SELECT 1 $$'
        assert to_drop(sql) == 'DROP FUNCTION "My Schema"."My Func"(int)'

    def test_or_replace(self):
        sql = "CREATE OR REPLACE FUNCTION public.add(a integer, b integer) RETURNS integer LANGUAGE sql AS $$ SELECT a + b $$"
        assert to_drop(sql) == "DROP FUNCTION public.add(int, int)"


class TestDropProcedure:
    def test_simple(self):
        sql = "CREATE PROCEDURE do_thing(x int) LANGUAGE sql AS $$ SELECT 1 $$"
        assert to_drop(sql) == "DROP PROCEDURE do_thing(int)"


class TestDropTrigger:
    def test_schema_qualified(self):
        sql = "CREATE TRIGGER my_trg BEFORE INSERT ON public.t FOR EACH ROW EXECUTE FUNCTION public.fn()"
        assert to_drop(sql) == "DROP TRIGGER my_trg ON public.t"

    def test_unqualified(self):
        sql = "CREATE TRIGGER my_trg BEFORE INSERT ON t FOR EACH ROW EXECUTE FUNCTION fn()"
        assert to_drop(sql) == "DROP TRIGGER my_trg ON t"


class TestDropView:
    def test_schema_qualified(self):
        assert to_drop("CREATE VIEW public.v AS SELECT 1") == "DROP VIEW public.v"

    def test_unqualified(self):
        assert to_drop("CREATE VIEW v AS SELECT 1") == "DROP VIEW v"

    def test_or_replace(self):
        assert to_drop("CREATE OR REPLACE VIEW public.v AS SELECT 1") == "DROP VIEW public.v"


class TestDropTable:
    def test_schema_qualified(self):
        assert to_drop("CREATE TABLE public.users (id int)") == "DROP TABLE public.users"

    def test_unqualified(self):
        assert to_drop("CREATE TABLE users (id int)") == "DROP TABLE users"

    def test_if_not_exists(self):
        assert to_drop("CREATE TABLE IF NOT EXISTS t (id int)") == "DROP TABLE t"

    def test_with_columns_and_constraints(self):
        sql = "CREATE TABLE t (id int PRIMARY KEY, name text NOT NULL, UNIQUE (name))"
        assert to_drop(sql) == "DROP TABLE t"


class TestDropIndex:
    def test_schema_qualified(self):
        assert to_drop("CREATE INDEX my_idx ON public.t (col)") == "DROP INDEX public.my_idx"

    def test_unqualified(self):
        assert to_drop("CREATE INDEX my_idx ON t (col)") == "DROP INDEX my_idx"

    def test_unique_index(self):
        assert to_drop("CREATE UNIQUE INDEX my_idx ON t (col)") == "DROP INDEX my_idx"

    def test_if_not_exists(self):
        assert to_drop("CREATE INDEX IF NOT EXISTS my_idx ON t (col)") == "DROP INDEX my_idx"


class TestDropSequence:
    def test_schema_qualified(self):
        assert to_drop("CREATE SEQUENCE public.my_seq") == "DROP SEQUENCE public.my_seq"

    def test_unqualified(self):
        assert to_drop("CREATE SEQUENCE my_seq") == "DROP SEQUENCE my_seq"

    def test_if_not_exists(self):
        assert to_drop("CREATE SEQUENCE IF NOT EXISTS my_seq") == "DROP SEQUENCE my_seq"


class TestDropSchema:
    def test_simple(self):
        assert to_drop("CREATE SCHEMA myschema") == "DROP SCHEMA myschema"

    def test_if_not_exists(self):
        assert to_drop("CREATE SCHEMA IF NOT EXISTS myschema") == "DROP SCHEMA myschema"


class TestDropType:
    def test_enum(self):
        assert to_drop("CREATE TYPE status AS ENUM ('active', 'inactive')") == "DROP TYPE status"

    def test_enum_schema_qualified(self):
        assert to_drop("CREATE TYPE public.status AS ENUM ('active')") == "DROP TYPE public.status"

    def test_range(self):
        assert to_drop("CREATE TYPE floatrange AS RANGE (subtype = float8)") == "DROP TYPE floatrange"

    def test_composite(self):
        assert to_drop("CREATE TYPE address AS (street text, city text)") == "DROP TYPE address"

    def test_composite_schema_qualified(self):
        assert to_drop("CREATE TYPE public.address AS (street text, city text)") == "DROP TYPE public.address"


class TestDropMaterializedView:
    def test_simple(self):
        assert to_drop("CREATE MATERIALIZED VIEW mv AS SELECT 1") == "DROP MATERIALIZED VIEW mv"

    def test_schema_qualified(self):
        assert to_drop("CREATE MATERIALIZED VIEW public.mv AS SELECT 1") == "DROP MATERIALIZED VIEW public.mv"


class TestErrors:
    def test_unsupported_statement(self):
        with pytest.raises(ValueError, match="unsupported statement type"):
            to_drop("SELECT 1")

    def test_multi_statement(self):
        with pytest.raises(ValueError, match="expected exactly one statement"):
            to_drop("CREATE VIEW v AS SELECT 1; CREATE VIEW w AS SELECT 2")

    def test_empty_input(self):
        with pytest.raises((ValueError, PgQueryError)):
            to_drop("")

    def test_invalid_sql(self):
        with pytest.raises(PgQueryError):
            to_drop("CREATE FUNCTION (")
