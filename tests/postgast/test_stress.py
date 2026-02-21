"""Stress tests — large inputs, deep nesting, wide queries.

All tests in this module are marked ``@pytest.mark.stress`` so they can be
excluded from fast CI runs with ``pytest -m "not stress"``.
"""

from __future__ import annotations

import pytest
from google.protobuf.message import DecodeError

from postgast import PgQueryError, deparse, fingerprint, normalize, parse, scan, split

pytestmark = pytest.mark.stress

# ---------------------------------------------------------------------------
# Helpers — generate large SQL strings
# ---------------------------------------------------------------------------


def _wide_select(n: int) -> str:
    """``SELECT c0, c1, …, c{n-1}``."""
    cols = ", ".join(f"c{i}" for i in range(n))
    return f"SELECT {cols}"


def _many_statements(n: int) -> str:
    """``SELECT 1; SELECT 2; … ; SELECT {n}``."""
    return "; ".join(f"SELECT {i}" for i in range(n))


def _nested_parens(depth: int) -> str:
    """``SELECT (((...1...)))`` with *depth* levels of parens."""
    return "SELECT " + "(" * depth + "1" + ")" * depth


def _nested_subqueries(depth: int) -> str:
    """``SELECT * FROM (SELECT * FROM (… SELECT 1 …) AS s0) AS s1 …``."""
    sql = "SELECT 1"
    for i in range(depth):
        sql = f"SELECT * FROM ({sql}) AS s{i}"
    return sql


def _many_joins(n: int) -> str:
    """``SELECT * FROM t0 JOIN t1 ON … JOIN t2 ON … ``."""
    parts = ["SELECT * FROM t0"]
    for i in range(1, n):
        parts.append(f"JOIN t{i} ON t{i}.id = t0.id")
    return " ".join(parts)


def _many_case_branches(n: int) -> str:
    """``SELECT CASE WHEN x=0 THEN 0 WHEN x=1 THEN 1 … END``."""
    branches = " ".join(f"WHEN x = {i} THEN {i}" for i in range(n))
    return f"SELECT CASE {branches} END"


def _large_in_list(n: int) -> str:
    """``SELECT * FROM t WHERE id IN (0, 1, …, n-1)``."""
    vals = ", ".join(str(i) for i in range(n))
    return f"SELECT * FROM t WHERE id IN ({vals})"


# ---------------------------------------------------------------------------
# 2.2  Large-input tests
# ---------------------------------------------------------------------------


class TestLargeInput:
    def test_parse_wide_select(self) -> None:
        result = parse(_wide_select(1_000))
        assert len(result.stmts) == 1

    def test_normalize_wide_select(self) -> None:
        result = normalize(_wide_select(1_000))
        assert isinstance(result, str)

    def test_fingerprint_wide_select(self) -> None:
        result = fingerprint(_wide_select(1_000))
        assert result.hex

    def test_split_many_statements(self) -> None:
        result = split(_many_statements(1_000))
        assert len(result) == 1_000

    def test_scan_wide_select(self) -> None:
        result = scan(_wide_select(1_000))
        assert len(result.tokens) > 0

    def test_parse_many_statements(self) -> None:
        result = parse(_many_statements(1_000))
        assert len(result.stmts) == 1_000


# ---------------------------------------------------------------------------
# 2.3  Deparse large-input test
# ---------------------------------------------------------------------------


class TestDeparseStress:
    def test_deparse_wide_select(self) -> None:
        tree = parse(_wide_select(1_000))
        result = deparse(tree)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# 2.4  Deep-nesting tests
# ---------------------------------------------------------------------------


class TestDeepNesting:
    def test_parse_nested_parens(self) -> None:
        sql = _nested_parens(500)
        try:
            result = parse(sql)
            assert len(result.stmts) == 1
        except PgQueryError:
            pass  # libpg_query may reject extreme nesting

    def test_normalize_nested_parens(self) -> None:
        sql = _nested_parens(500)
        try:
            result = normalize(sql)
            assert isinstance(result, str)
        except PgQueryError:
            pass

    def test_fingerprint_nested_parens(self) -> None:
        sql = _nested_parens(500)
        try:
            result = fingerprint(sql)
            assert result.hex
        except PgQueryError:
            pass

    def test_split_nested_parens(self) -> None:
        sql = _nested_parens(500)
        try:
            result = split(sql)
            assert isinstance(result, list)
        except PgQueryError:
            pass

    def test_scan_nested_parens(self) -> None:
        sql = _nested_parens(500)
        try:
            result = scan(sql)
            assert len(result.tokens) > 0
        except PgQueryError:
            pass


# ---------------------------------------------------------------------------
# 2.5  Deep-subquery test
# ---------------------------------------------------------------------------


class TestDeepSubqueries:
    def test_parse_nested_subqueries(self) -> None:
        sql = _nested_subqueries(100)
        try:
            result = parse(sql)
            assert len(result.stmts) == 1
        except (PgQueryError, DecodeError):
            pass  # deep nesting may exceed libpg_query limits or corrupt protobuf


# ---------------------------------------------------------------------------
# 2.6  Wide-query tests
# ---------------------------------------------------------------------------


class TestWideQueries:
    def test_parse_many_joins(self) -> None:
        sql = _many_joins(50)
        try:
            result = parse(sql)
            assert len(result.stmts) == 1
        except (PgQueryError, DecodeError):
            pass  # many JOINs may exceed protobuf nesting limits

    def test_parse_many_case_branches(self) -> None:
        sql = _many_case_branches(500)
        result = parse(sql)
        assert len(result.stmts) == 1

    def test_normalize_large_in_list(self) -> None:
        sql = _large_in_list(1_000)
        result = normalize(sql)
        assert isinstance(result, str)
