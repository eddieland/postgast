"""Base class, registry, and helper functions for typed AST wrappers."""

# ruff: noqa: D105,D107

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from google.protobuf.message import Message


class AstNode:
    """Base class for all typed AST wrappers."""

    __slots__ = ("_pb",)

    def __init__(self, pb: Message) -> None:
        self._pb = pb

    def __repr__(self) -> str:
        return f"{type(self).__name__}(...)"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AstNode):
            return self._pb == other._pb
        return NotImplemented  # type: ignore[return-value]

    def __hash__(self) -> int:
        return id(self._pb)


_REGISTRY: dict[str, type[AstNode]] = {}


def _wrap(pb: Message) -> AstNode:
    """Wrap a protobuf message in its typed AST wrapper."""
    desc = type(pb).DESCRIPTOR
    # Unwrap Node oneof if needed
    if len(desc.oneofs) == 1 and desc.oneofs[0].name == "node":
        which = pb.WhichOneof("node")
        if which is not None:
            pb = getattr(pb, which)
    cls = _REGISTRY.get(type(pb).DESCRIPTOR.name, AstNode)
    return cls(pb)


def _wrap_node_optional(pb: Message) -> AstNode | None:
    """Wrap a Node oneof field, returning None if unset."""
    which = pb.WhichOneof("node")
    if which is None:
        return None
    inner = getattr(pb, which)
    cls = _REGISTRY.get(type(inner).DESCRIPTOR.name, AstNode)
    return cls(inner)


def _wrap_list(repeated: Iterable[Message]) -> list[AstNode]:
    """Wrap a repeated Node field into a list of typed wrappers."""
    result: list[AstNode] = []
    for item in repeated:
        which = item.WhichOneof("node")
        if which is not None:
            inner = getattr(item, which)
            cls = _REGISTRY.get(type(inner).DESCRIPTOR.name, AstNode)
            result.append(cls(inner))
    return result


def wrap(tree: Message) -> AstNode:
    """Wrap a protobuf message tree in typed AST wrappers.

    This is the main entry point. Pass a ``ParseResult`` from ``postgast.parse()`` to get a fully typed wrapper tree.

    Args:
        tree: Any protobuf ``Message`` (typically ``ParseResult``).

    Returns:
        A typed ``AstNode`` wrapper. Access fields as properties; nested nodes are wrapped lazily on access.

    Example:
        >>> from postgast import parse
        >>> from postgast.nodes import wrap, SelectStmt
        >>> tree = wrap(parse("SELECT 1"))
        >>> stmt = tree.stmts[0].stmt
        >>> isinstance(stmt, SelectStmt)
        True
    """
    if isinstance(tree, AstNode):
        return tree
    return _wrap(tree)
