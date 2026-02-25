"""Convenience functions for extracting common information from parsed SQL ASTs."""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, TypeVar

from google.protobuf.message import Message

from postgast.pg_query_pb2 import (
    FUNC_PARAM_DEFAULT,
    FUNC_PARAM_IN,
    FUNC_PARAM_INOUT,
    FUNC_PARAM_VARIADIC,
    OBJECT_FUNCTION,
    OBJECT_PROCEDURE,
    OBJECT_TRIGGER,
    OBJECT_VIEW,
    A_Star,
    ColumnRef,
    CreateFunctionStmt,
    CreateTrigStmt,
    DropStmt,
    FuncCall,
    ObjectWithArgs,
    ParseResult,
    RangeVar,
    String,
    ViewStmt,
)
from postgast.walk import walk

if TYPE_CHECKING:
    from collections.abc import Generator

_M = TypeVar("_M", bound=Message)
_OR_REPLACE_TYPES = (CreateFunctionStmt, CreateTrigStmt, ViewStmt)


class FunctionIdentity(typing.NamedTuple):
    """Identity parts of a ``CREATE FUNCTION`` statement.

    Attributes:
        schema: Schema name, or ``None`` for unqualified functions.
        name: Function name.
    """

    schema: str | None
    name: str


class TriggerIdentity(typing.NamedTuple):
    """Identity parts of a ``CREATE TRIGGER`` statement.

    Attributes:
        trigger: Trigger name.
        schema: Schema qualifying the target table, or ``None``.
        table: Target table name.
    """

    trigger: str
    schema: str | None
    table: str


def find_nodes(tree: Message, node_type: type[_M]) -> Generator[_M, None, None]:
    """Yield all protobuf messages matching *node_type* from a parse tree.

    Walks the tree in depth-first pre-order (same as :func:`walk`) and yields every message that is an instance of
    *node_type*.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).
        node_type: Protobuf message class to match (e.g., ``RangeVar``).

    Yields:
        Matching instances in depth-first pre-order.

    Example:
        >>> from postgast import find_nodes, parse
        >>> from postgast.pg_query_pb2 import RangeVar
        >>> tree = parse("SELECT * FROM users JOIN orders ON users.id = orders.uid")
        >>> [n.relname for n in find_nodes(tree, RangeVar)]
        ['users', 'orders']
    """
    for _field_name, node in walk(tree):
        if isinstance(node, node_type):
            yield node


def extract_tables(tree: Message) -> Generator[str, None, None]:
    """Yield table names referenced in a parse tree.

    Walks all ``RangeVar`` nodes and yields their names as dot-joined strings (``"schema.table"`` when
    schema-qualified, ``"table"`` otherwise).

    Results preserve encounter order and include duplicates. Use ``set()`` on the result to get unique table names.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Yields:
        Table names in encounter order.

    Example:
        >>> from postgast import extract_tables, parse
        >>> tree = parse("SELECT * FROM public.users JOIN orders ON true")
        >>> list(extract_tables(tree))
        ['public.users', 'orders']
    """
    for node in find_nodes(tree, RangeVar):
        yield f"{node.schemaname}.{node.relname}" if node.schemaname else node.relname


def extract_columns(tree: Message) -> Generator[str, None, None]:
    """Yield column references found in a parse tree.

    Walks all ``ColumnRef`` nodes and yields their names as dot-joined strings. ``SELECT *`` produces ``"*"``;
    ``t.*`` produces ``"t.*"``.

    Results preserve encounter order and include duplicates.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Yields:
        Column references in encounter order.

    Example:
        >>> from postgast import extract_columns, parse
        >>> tree = parse("SELECT u.name, age FROM users u WHERE age > 18")
        >>> list(extract_columns(tree))
        ['u.name', 'age', 'age']
    """
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
        yield ".".join(parts)


def extract_functions(tree: Message) -> Generator[str, None, None]:
    """Yield function call names found in a parse tree.

    Walks all ``FuncCall`` nodes and yields their names as dot-joined strings (``"schema.func"`` when
    schema-qualified, ``"func"`` otherwise).

    Results preserve encounter order and include duplicates.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Yields:
        Function names in encounter order.

    Example:
        >>> from postgast import extract_functions, parse
        >>> tree = parse("SELECT lower(name), count(*) FROM users")
        >>> list(extract_functions(tree))
        ['lower', 'count']
    """
    for node in find_nodes(tree, FuncCall):
        parts: list[str] = []
        for name_node in node.funcname:
            which = name_node.WhichOneof("node")
            if which is not None:
                inner = getattr(name_node, which)
                if isinstance(inner, String):
                    parts.append(inner.sval)
        yield ".".join(parts)


def extract_function_identity(tree: Message) -> FunctionIdentity | None:
    """Return the identity of the first ``CREATE FUNCTION`` statement in a parse tree.

    Finds the first ``CreateFunctionStmt`` node where ``is_procedure`` is ``False`` and returns a
    :class:`FunctionIdentity` with the schema and function name.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        A :class:`FunctionIdentity` or ``None`` if no matching node is found.

    Example:
        >>> from postgast import extract_function_identity, parse
        >>> sql = "CREATE FUNCTION public.add(a int, b int) RETURNS int LANGUAGE sql AS $$ SELECT a + b $$"
        >>> identity = extract_function_identity(parse(sql))
        >>> identity.schema, identity.name
        ('public', 'add')
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

    Finds the first ``CreateTrigStmt`` node and returns a :class:`TriggerIdentity` with the trigger name, schema,
    and table name.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        A :class:`TriggerIdentity` or ``None`` if no matching node is found.

    Example:
        >>> from postgast import extract_trigger_identity, parse
        >>> sql = "CREATE TRIGGER my_trg AFTER INSERT ON orders FOR EACH ROW EXECUTE FUNCTION notify()"
        >>> identity = extract_trigger_identity(parse(sql))
        >>> identity.trigger, identity.table
        ('my_trg', 'orders')
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

    Walks *tree* and flips the ``replace`` flag on ``CreateFunctionStmt``, ``CreateTrigStmt``, and ``ViewStmt`` nodes
    where it is currently ``False``.

    Args:
        tree: A protobuf ``Message`` (typically a ``ParseResult``).

    Returns:
        Number of nodes that were modified.

    Example:
        >>> from postgast import set_or_replace, parse, deparse
        >>> tree = parse("CREATE VIEW v AS SELECT 1")
        >>> set_or_replace(tree)
        1
        >>> "OR REPLACE" in deparse(tree)
        True
    """
    count = 0
    for _field_name, node in walk(tree):
        if isinstance(node, _OR_REPLACE_TYPES) and not node.replace:
            node.replace = True
            count += 1
    return count


def ensure_or_replace(sql: str) -> str:
    """Return *sql* with all eligible ``CREATE`` statements rewritten to ``CREATE OR REPLACE``.

    Parses the input, sets ``replace = True`` on ``CreateFunctionStmt``, ``CreateTrigStmt``, and ``ViewStmt`` nodes,
    and deparses back to SQL.

    Args:
        sql: One or more SQL statements.

    Returns:
        The rewritten SQL text.

    Raises:
        PgQueryError: If *sql* cannot be parsed.

    Example:
        >>> from postgast import ensure_or_replace
        >>> ensure_or_replace("CREATE VIEW v AS SELECT 1")
        'CREATE OR REPLACE VIEW v AS SELECT 1'
    """
    from postgast.deparse import deparse
    from postgast.parse import parse

    tree = parse(sql)
    set_or_replace(tree)
    return deparse(tree)


_IDENTITY_MODES = frozenset({FUNC_PARAM_IN, FUNC_PARAM_INOUT, FUNC_PARAM_VARIADIC, FUNC_PARAM_DEFAULT})


def _drop_function(stmt: CreateFunctionStmt) -> DropStmt:
    """Build a DropStmt for a CREATE FUNCTION or CREATE PROCEDURE."""
    drop = DropStmt()
    drop.remove_type = OBJECT_PROCEDURE if stmt.is_procedure else OBJECT_FUNCTION

    owa = ObjectWithArgs()
    for name_node in stmt.funcname:
        owa.objname.add().CopyFrom(name_node)
    for param_node in stmt.parameters:
        fp = param_node.function_parameter
        if fp.mode not in _IDENTITY_MODES:
            continue
        owa.objargs.add().type_name.CopyFrom(fp.arg_type)

    drop.objects.add().object_with_args.CopyFrom(owa)
    return drop


def _drop_trigger(stmt: CreateTrigStmt) -> DropStmt:
    """Build a DropStmt for a CREATE TRIGGER."""
    drop = DropStmt()
    drop.remove_type = OBJECT_TRIGGER

    lst = drop.objects.add().list
    if stmt.relation.schemaname:
        lst.items.add().string.sval = stmt.relation.schemaname
    lst.items.add().string.sval = stmt.relation.relname
    lst.items.add().string.sval = stmt.trigname
    return drop


def _drop_view(stmt: ViewStmt) -> DropStmt:
    """Build a DropStmt for a CREATE VIEW."""
    drop = DropStmt()
    drop.remove_type = OBJECT_VIEW

    lst = drop.objects.add().list
    if stmt.view.schemaname:
        lst.items.add().string.sval = stmt.view.schemaname
    lst.items.add().string.sval = stmt.view.relname
    return drop


def to_drop(sql: str) -> str:
    """Return the ``DROP`` statement corresponding to a ``CREATE`` statement.

    Parses *sql*, builds a ``DropStmt`` protobuf from the parsed AST, and deparses it back to SQL. Supports ``CREATE
    FUNCTION``, ``CREATE PROCEDURE``, ``CREATE TRIGGER``, and ``CREATE VIEW`` (including ``OR REPLACE`` variants).

    Args:
        sql: A single CREATE statement.

    Returns:
        The corresponding DROP statement.

    Raises:
        ValueError: If *sql* contains zero or more than one statement, or if the statement is not a supported CREATE
            type.
        PgQueryError: If *sql* is not valid SQL.

    Example:
        >>> from postgast import to_drop
        >>> to_drop("CREATE VIEW public.v AS SELECT 1")
        'DROP VIEW public.v'
    """
    from postgast.deparse import deparse
    from postgast.parse import parse

    tree = parse(sql)

    if len(tree.stmts) != 1:
        msg = f"expected exactly one statement, got {len(tree.stmts)}"
        raise ValueError(msg)

    node = tree.stmts[0].stmt
    which = node.WhichOneof("node")

    if which == "create_function_stmt":
        drop = _drop_function(node.create_function_stmt)
    elif which == "create_trig_stmt":
        drop = _drop_trigger(node.create_trig_stmt)
    elif which == "view_stmt":
        drop = _drop_view(node.view_stmt)
    else:
        msg = f"unsupported statement type: {which}"
        raise ValueError(msg)

    result = ParseResult()
    result.stmts.add().stmt.drop_stmt.CopyFrom(drop)
    return deparse(result)
