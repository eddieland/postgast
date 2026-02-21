"""Convenience functions for extracting common information from parsed SQL ASTs."""

from __future__ import annotations

from collections.abc import Generator

from google.protobuf.message import Message

from postgast._walk import walk


def find_nodes(tree: Message, node_type: str) -> Generator[Message, None, None]:
    """Yield all protobuf messages matching *node_type* from a parse tree.

    Walks the tree in depth-first pre-order (same as :func:`walk`) and yields
    every message whose protobuf descriptor name equals *node_type*.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).
        node_type: Protobuf descriptor name to match (e.g., ``"RangeVar"``).

    Yields:
        Matching ``Message`` instances in depth-first pre-order.
    """
    for _field_name, node in walk(tree):
        if type(node).DESCRIPTOR.name == node_type:
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
    for node in find_nodes(tree, "RangeVar"):
        schema: str = node.schemaname  # pyright: ignore[reportAttributeAccessIssue,reportAssignmentType]
        rel: str = node.relname  # pyright: ignore[reportAttributeAccessIssue,reportAssignmentType]
        tables.append(f"{schema}.{rel}" if schema else rel)
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
    for node in find_nodes(tree, "ColumnRef"):
        parts: list[str] = []
        for field_node in node.fields:  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType,reportUnknownMemberType]
            descriptor_name = type(field_node).DESCRIPTOR.name
            if descriptor_name == "Node":
                which = field_node.WhichOneof("node")
                if which is not None:
                    inner = getattr(field_node, which)
                    inner_name = type(inner).DESCRIPTOR.name
                    if inner_name == "String":
                        parts.append(inner.sval)
                    elif inner_name == "A_Star":
                        parts.append("*")
            elif descriptor_name == "String":
                parts.append(field_node.sval)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
            elif descriptor_name == "A_Star":
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
    for node in find_nodes(tree, "FuncCall"):
        parts: list[str] = []
        for name_node in node.funcname:  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType,reportUnknownMemberType]
            descriptor_name = type(name_node).DESCRIPTOR.name
            if descriptor_name == "Node":
                which = name_node.WhichOneof("node")
                if which is not None:
                    inner = getattr(name_node, which)
                    if type(inner).DESCRIPTOR.name == "String":
                        parts.append(inner.sval)
            elif descriptor_name == "String":
                parts.append(name_node.sval)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        functions.append(".".join(parts))
    return functions
