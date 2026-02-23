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
