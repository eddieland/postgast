"""Property-based fuzz tests for the ctypes/libpg_query boundary.

All tests in this module are marked ``@pytest.mark.fuzz`` so they are
excluded from the default ``make test`` run.  Use ``make fuzz`` to execute.
"""

from __future__ import annotations

import os
import random

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings
from hypothesis import strategies as st

from postgast import ParseResult, PgQueryError, deparse, fingerprint, normalize, parse, scan, split

pytestmark = pytest.mark.fuzz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_EXAMPLES = int(os.environ.get("HYPOTHESIS_MAX_EXAMPLES", "1000"))

# ---------------------------------------------------------------------------
# SQL-biased input strategy
# ---------------------------------------------------------------------------

_SQL_KEYWORDS = [
    "SELECT",
    "FROM",
    "WHERE",
    "INSERT",
    "INTO",
    "UPDATE",
    "DELETE",
    "CREATE",
    "DROP",
    "ALTER",
    "TABLE",
    "INDEX",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "ON",
    "AND",
    "OR",
    "NOT",
    "NULL",
    "IS",
    "IN",
    "AS",
    "ORDER",
    "BY",
    "GROUP",
    "HAVING",
    "LIMIT",
    "OFFSET",
    "UNION",
    "ALL",
    "EXISTS",
    "BETWEEN",
    "LIKE",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "WITH",
    "RECURSIVE",
    "VALUES",
    "SET",
    "DEFAULT",
    "PRIMARY",
    "KEY",
    "FOREIGN",
    "REFERENCES",
    "CHECK",
    "CONSTRAINT",
    "UNIQUE",
    "CASCADE",
    "RESTRICT",
    "GRANT",
    "REVOKE",
    "RETURNING",
]

_SQL_OPERATORS = ["=", "<>", "!=", "<", ">", "<=", ">=", "||", "+", "-", "*", "/", "%", "~", "!~", "::"]

_SQL_PUNCTUATION = [";", "(", ")", ",", ".", "'", '"', "$", "@", "#", "{", "}", "[", "]", "\\"]

_sql_keyword = st.sampled_from(_SQL_KEYWORDS)
_sql_operator = st.sampled_from(_SQL_OPERATORS)
_sql_punctuation = st.sampled_from(_SQL_PUNCTUATION)
_sql_identifier = st.from_regex(r"[a-z_][a-z0-9_]{0,15}", fullmatch=True)
_sql_literal = st.one_of(
    st.integers(-999999, 999999).map(str),
    st.from_regex(r"'[^']{0,20}'", fullmatch=True),
)

_sql_fragment = st.lists(
    st.one_of(_sql_keyword, _sql_operator, _sql_punctuation, _sql_identifier, _sql_literal),
    min_size=1,
    max_size=30,
).map(" ".join)

_edge_cases = st.one_of(
    st.just(""),
    st.just("\x00"),
    st.just("SELECT 1" + "\x00" + "SELECT 2"),
    st.text(alphabet="\x00", min_size=1, max_size=100),
    st.just("SELECT " + "x" * 100_000),
    st.just("(" * 500 + "1" + ")" * 500),
)

sql_input = st.one_of(
    st.text(),
    st.binary().map(lambda b: b.decode("utf-8", errors="replace")),
    _sql_fragment,
    _edge_cases,
)

# ---------------------------------------------------------------------------
# Pool of valid SQL for deparse tests
# ---------------------------------------------------------------------------

_VALID_SQL_POOL = [
    "SELECT 1",
    "SELECT * FROM t",
    "SELECT a, b FROM t WHERE x = 1",
    "INSERT INTO t (a) VALUES (1)",
    "UPDATE t SET a = 1 WHERE b = 2",
    "DELETE FROM t WHERE x = 1",
    "SELECT a FROM t ORDER BY a LIMIT 10",
    "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
    "SELECT count(*) FROM t GROUP BY a HAVING count(*) > 1",
    "WITH cte AS (SELECT 1 AS n) SELECT * FROM cte",
    "SELECT CASE WHEN x = 1 THEN 'a' ELSE 'b' END FROM t",
    "CREATE TABLE t (id int PRIMARY KEY, name text)",
    "SELECT * FROM t WHERE x IN (1, 2, 3)",
    "SELECT * FROM t WHERE x BETWEEN 1 AND 10",
    "SELECT a, b, c FROM t1 LEFT JOIN t2 ON t1.id = t2.fk",
]


# ---------------------------------------------------------------------------
# 3. String-accepting function fuzz tests
# ---------------------------------------------------------------------------


class TestFuzz:
    @settings(max_examples=MAX_EXAMPLES)
    @given(sql=sql_input)
    def test_parse_does_not_crash(self, sql: str) -> None:
        try:
            result = parse(sql)
            assert isinstance(result, ParseResult)
        except PgQueryError:
            pass

    @settings(max_examples=MAX_EXAMPLES)
    @given(sql=sql_input)
    def test_normalize_does_not_crash(self, sql: str) -> None:
        try:
            result = normalize(sql)
            assert isinstance(result, str)
        except PgQueryError:
            pass

    @settings(max_examples=MAX_EXAMPLES)
    @given(sql=sql_input)
    def test_fingerprint_does_not_crash(self, sql: str) -> None:
        try:
            result = fingerprint(sql)
            assert isinstance(result.hex, str)
        except PgQueryError:
            pass

    @settings(max_examples=MAX_EXAMPLES)
    @given(sql=sql_input)
    def test_scan_does_not_crash(self, sql: str) -> None:
        try:
            result = scan(sql)
            assert result is not None
        except PgQueryError:
            pass

    @settings(max_examples=MAX_EXAMPLES)
    @given(sql=sql_input)
    def test_split_does_not_crash(self, sql: str) -> None:
        try:
            result = split(sql)
            assert isinstance(result, list)
        except PgQueryError:
            pass

    # -------------------------------------------------------------------
    # 4. Deparse fuzz tests
    # -------------------------------------------------------------------

    @settings(max_examples=MAX_EXAMPLES)
    @given(sql=st.sampled_from(_VALID_SQL_POOL))
    def test_deparse_roundtrip_does_not_crash(self, sql: str) -> None:
        tree = parse(sql)
        result = deparse(tree)
        assert isinstance(result, str)

    @settings(max_examples=MAX_EXAMPLES)
    @given(sql=st.sampled_from(_VALID_SQL_POOL), seed=st.integers(0, 2**32 - 1))
    def test_deparse_mutated_tree_does_not_crash(self, sql: str, seed: int) -> None:
        tree = parse(sql)
        rng = random.Random(seed)
        _mutate_parse_result(tree, rng)
        try:
            result = deparse(tree)
            assert isinstance(result, str)
        except PgQueryError:
            pass


# ---------------------------------------------------------------------------
# Helpers for tree mutation
# ---------------------------------------------------------------------------


def _mutate_parse_result(tree: ParseResult, rng: random.Random) -> None:
    """Apply random mutations to a ParseResult to exercise deparse with malformed ASTs.

    Mutations are kept structurally conservative to avoid triggering segfaults
    in libpg_query's C code.  We mutate at the statement level (swap, duplicate,
    clear the stmt oneof) rather than clearing arbitrary inner fields, which can
    leave the protobuf in a state that crashes the C deparsing code.
    """
    if not tree.stmts:
        return

    mutation = rng.choice(["swap_stmts", "duplicate_stmt", "clear_stmt", "set_version"])

    if mutation == "swap_stmts" and len(tree.stmts) >= 2:
        i, j = rng.sample(range(len(tree.stmts)), 2)
        tree.stmts[i].CopyFrom(tree.stmts[j])

    elif mutation == "duplicate_stmt" and tree.stmts:
        src = rng.choice(list(tree.stmts))
        new_stmt = tree.stmts.add()
        new_stmt.CopyFrom(src)

    elif mutation == "clear_stmt" and tree.stmts:
        idx = rng.randrange(len(tree.stmts))
        tree.stmts[idx].ClearField("stmt")

    elif mutation == "set_version":
        tree.version = rng.randint(0, 2**31 - 1)
