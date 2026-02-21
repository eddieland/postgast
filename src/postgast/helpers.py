"""Convenience functions for extracting common information from parsed SQL ASTs."""

from __future__ import annotations

import typing
from collections.abc import Generator
from typing import TypeVar

from google.protobuf.message import Message

from postgast.pg_query_pb2 import (
    A_Star,
    ColumnRef,
    CreateFunctionStmt,
    CreateTrigStmt,
    FuncCall,
    RangeVar,
    String,
    ViewStmt,
)
from postgast.walk import walk

_M = TypeVar("_M", bound=Message)
_OR_REPLACE_TYPES = (CreateFunctionStmt, CreateTrigStmt, ViewStmt)


class FunctionIdentity(typing.NamedTuple):
    """Identity parts of a ``CREATE FUNCTION`` statement."""

    schema: str | None
    name: str


class TriggerIdentity(typing.NamedTuple):
    """Identity parts of a ``CREATE TRIGGER`` statement."""

    trigger: str
    schema: str | None
    table: str


def find_nodes(tree: Message, node_type: type[_M]) -> Generator[_M, None, None]:
    """Yield all protobuf messages matching *node_type* from a parse tree.

    Walks the tree in depth-first pre-order (same as :func:`walk`) and yields
    every message that is an instance of *node_type*.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).
        node_type: Protobuf message class to match (e.g., ``RangeVar``).

    Yields:
        Matching instances in depth-first pre-order.
    """
    for _field_name, node in walk(tree):
        if isinstance(node, node_type):
            yield node


def extract_tables(tree: Message) -> list[str]:
    """Return table names referenced in a parse tree.

    Collects all ``RangeVar`` nodes and returns their names as dot-joined
    strings (``"schema.table"`` when schema-qualified, ``"table"`` otherwise).

    Results preserve encounter order and include duplicates. Use ``set()`` on
    the result to get unique table names.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        Table names in encounter order.
    """
    tables: list[str] = []
    for node in find_nodes(tree, RangeVar):
        tables.append(f"{node.schemaname}.{node.relname}" if node.schemaname else node.relname)
    return tables


def extract_columns(tree: Message) -> list[str]:
    """Return column references found in a parse tree.

    Collects all ``ColumnRef`` nodes and returns their names as dot-joined
    strings. ``SELECT *`` produces ``"*"``; ``t.*`` produces ``"t.*"``.

    Results preserve encounter order and include duplicates.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        Column references in encounter order.
    """
    columns: list[str] = []
    for node in find_nodes(tree, ColumnRef):
        parts: list[str] = []
        for field_node in node.fields:
            which = field_node.WhichOneof("node")
            if which is not None:
                inner = getattr(field_node, which)
                if isinstance(inner, String):
                    parts.append(inner.sval)
                elif isinstance(inner, A_Star):
                    parts.append("*")
        columns.append(".".join(parts))
    return columns


def extract_functions(tree: Message) -> list[str]:
    """Return function call names found in a parse tree.

    Collects all ``FuncCall`` nodes and returns their names as dot-joined
    strings (``"schema.func"`` when schema-qualified, ``"func"`` otherwise).

    Results preserve encounter order and include duplicates.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        Function names in encounter order.
    """
    functions: list[str] = []
    for node in find_nodes(tree, FuncCall):
        parts: list[str] = []
        for name_node in node.funcname:
            which = name_node.WhichOneof("node")
            if which is not None:
                inner = getattr(name_node, which)
                if isinstance(inner, String):
                    parts.append(inner.sval)
        functions.append(".".join(parts))
    return functions


def extract_function_identity(tree: Message) -> FunctionIdentity | None:
    """Return the identity of the first ``CREATE FUNCTION`` statement in a parse tree.

    Finds the first ``CreateFunctionStmt`` node where ``is_procedure`` is ``False``
    and returns a :class:`FunctionIdentity` with the schema and function name.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        A :class:`FunctionIdentity` or ``None`` if no matching node is found.
    """
    for node in find_nodes(tree, CreateFunctionStmt):
        if node.is_procedure:
            continue
        parts: list[str] = []
        for name_node in node.funcname:
            which = name_node.WhichOneof("node")
            if which is not None:
                inner = getattr(name_node, which)
                if isinstance(inner, String):
                    parts.append(inner.sval)
        if len(parts) == 2:
            return FunctionIdentity(schema=parts[0], name=parts[1])
        if len(parts) == 1:
            return FunctionIdentity(schema=None, name=parts[0])
    return None


def extract_trigger_identity(tree: Message) -> TriggerIdentity | None:
    """Return the identity of the first ``CREATE TRIGGER`` statement in a parse tree.

    Finds the first ``CreateTrigStmt`` node and returns a :class:`TriggerIdentity`
    with the trigger name, schema, and table name.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        A :class:`TriggerIdentity` or ``None`` if no matching node is found.
    """
    for node in find_nodes(tree, CreateTrigStmt):
        return TriggerIdentity(
            trigger=node.trigname,
            schema=node.relation.schemaname or None,
            table=node.relation.relname,
        )
    return None


def set_or_replace(tree: Message) -> int:
    """Set ``replace = True`` on eligible DDL nodes in a parse tree.

    Walks *tree* and flips the ``replace`` flag on
    ``CreateFunctionStmt``, ``CreateTrigStmt``, and ``ViewStmt`` nodes
    where it is currently ``False``.

    Args:
        tree: A protobuf ``Message`` (typically a ``ParseResult``).

    Returns:
        Number of nodes that were modified.
    """
    count = 0
    for _field_name, node in walk(tree):
        if isinstance(node, _OR_REPLACE_TYPES):
            if not node.replace:
                node.replace = True
                count += 1
    return count


def ensure_or_replace(sql: str) -> str:
    """Return *sql* with all eligible ``CREATE`` statements rewritten to ``CREATE OR REPLACE``.

    Parses the input, sets ``replace = True`` on ``CreateFunctionStmt``,
    ``CreateTrigStmt``, and ``ViewStmt`` nodes, and deparses back to SQL.

    Args:
        sql: One or more SQL statements.

    Returns:
        The rewritten SQL text.

    Raises:
        PgQueryError: If *sql* cannot be parsed.
    """
    from postgast.deparse import deparse
    from postgast.parse import parse

    tree = parse(sql)
    set_or_replace(tree)
    return deparse(tree)
