"""Utility functions for identifier quoting and name conversion."""

from __future__ import annotations

import functools
import re
from typing import Final

import postgast.pg_query_pb2 as pb
from postgast.scan import scan as _scan

_SIMPLE_IDENT_RE: Final = re.compile(r"^[a-z_][a-z0-9_]*$")


@functools.lru_cache(maxsize=256)
def _needs_quoting(name: str) -> bool:
    if not _SIMPLE_IDENT_RE.match(name):
        return True
    result = _scan(f"SELECT {name}")
    tokens = list(result.tokens)
    return len(tokens) >= 2 and tokens[1].keyword_kind == pb.RESERVED_KEYWORD


def _quote_ident(name: str) -> str:
    if _needs_quoting(name):
        escaped = name.replace('"', '""')
        return f'"{escaped}"'
    return name


@functools.lru_cache(maxsize=256)
def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case (e.g. ``SelectStmt`` → ``select_stmt``).

    The regex only splits at lowercase/digit → uppercase boundaries, so leading acronyms stay grouped
    (``SQLValueFunction`` → ``sqlvalue_function``).  This intentionally matches protobuf's own field-name
    convention in ``Node.__slots__``.
    """
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()
