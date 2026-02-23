from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from postgast import ParseResult, PgQueryError, deparse, parse

if TYPE_CHECKING:
    from collections.abc import Callable

# -- Parse-result fixtures (function scope for independent protobuf instances) --


@pytest.fixture
def select1_tree() -> ParseResult:
    return parse("SELECT 1")


@pytest.fixture
def create_table_tree() -> ParseResult:
    return parse("CREATE TABLE t (id int PRIMARY KEY, name text)")


@pytest.fixture
def multi_stmt_tree() -> ParseResult:
    return parse("SELECT 1; SELECT 2")


@pytest.fixture
def users_tree() -> ParseResult:
    return parse("SELECT * FROM users")


# -- Assertion helpers ---------------------------------------------------------


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


def assert_pg_query_error(fn: Callable[..., Any], sql: str, *, check_cursorpos: bool = False) -> None:
    """Assert that calling fn(sql) raises PgQueryError with a truthy message."""
    with pytest.raises(PgQueryError) as exc_info:
        fn(sql)
    assert exc_info.value.message
    if check_cursorpos:
        assert exc_info.value.cursorpos > 0
