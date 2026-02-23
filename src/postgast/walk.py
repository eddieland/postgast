"""Tree walking and visitor pattern for protobuf parse trees."""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.protobuf.descriptor import FieldDescriptor

if TYPE_CHECKING:
    from collections.abc import Generator

    from google.protobuf.message import Message

_NODE_ONEOF = "node"


def _unwrap_node(node: Message) -> Message:
    """If *node* is a ``Node`` oneof wrapper, return the inner concrete message; otherwise return *node* unchanged."""
    oneofs = type(node).DESCRIPTOR.oneofs
    if len(oneofs) == 1 and oneofs[0].name == _NODE_ONEOF:
        which = node.WhichOneof(_NODE_ONEOF)
        if which is not None:
            return getattr(node, which)
    return node


def _iter_children(node: Message) -> Generator[tuple[str, Message], None, None]:
    """Yield ``(field_name, child_message)`` for every message-typed field set on *node*, unwrapping ``Node`` wrappers."""
    for fd, value in node.ListFields():
        if fd.type != FieldDescriptor.TYPE_MESSAGE:
            continue
        if fd.is_repeated:
            for item in value:
                yield fd.name, _unwrap_node(item)
        else:
            yield fd.name, _unwrap_node(value)


def walk(node: Message) -> Generator[tuple[str, Message], None, None]:
    """Depth-first pre-order traversal of a protobuf message tree.

    Yields ``(field_name, message)`` tuples for every protobuf message
    encountered. The *field_name* is the protobuf field name that led to
    the message (e.g. ``"where_clause"``, ``"target_list"``), or an empty
    string for the root.

    ``Node`` oneof wrappers are transparently unwrapped so that only
    concrete message types appear in the output.

    Args:
        node: Any protobuf ``Message`` instance (``ParseResult``,
            ``SelectStmt``, etc.).

    Yields:
        ``(field_name, message)`` tuples in depth-first pre-order.

    Example:
        >>> from postgast import parse, walk
        >>> tree = parse("SELECT 1")
        >>> for field_name, node in walk(tree):
        ...     if field_name:
        ...         print(f"{field_name}: {type(node).__name__}")
        stmts: RawStmt
        stmt: SelectStmt
        target_list: ResTarget
        val: A_Const
    """
    node = _unwrap_node(node)
    yield "", node
    stack: list[tuple[str, Message]] = list(reversed(list(_iter_children(node))))
    while stack:
        field_name, child = stack.pop()
        yield field_name, child
        stack.extend(reversed(list(_iter_children(child))))


class Visitor:
    """Base class for protobuf parse tree visitors.

    Subclass and override ``visit_<TypeName>`` methods (e.g.
    ``visit_SelectStmt``, ``visit_ColumnRef``) to handle specific node
    types. Unhandled types fall through to :meth:`generic_visit` which
    recurses into children.

    Call :meth:`visit` on a root message to start traversal::

        class TableCollector(Visitor):
            def __init__(self):
                self.tables = []

            def visit_RangeVar(self, node):
                self.tables.append(node.relname)


        collector = TableCollector()
        collector.visit(parse_result)
    """

    def visit(self, node: Message) -> None:
        """Dispatch *node* to ``visit_<TypeName>`` or :meth:`generic_visit`.

        Looks up a method named ``visit_<TypeName>`` (where ``<TypeName>``
        matches the protobuf descriptor name, e.g. ``visit_SelectStmt``).
        Falls back to :meth:`generic_visit` if no specific handler exists.

        Args:
            node: Any protobuf ``Message`` instance.
        """
        node = _unwrap_node(node)
        type_name = type(node).DESCRIPTOR.name
        handler = getattr(self, f"visit_{type_name}", self.generic_visit)
        handler(node)

    def generic_visit(self, node: Message) -> None:
        """Visit all message-typed children of *node*.

        Override this method to customize the default traversal behavior.
        Call ``super().generic_visit(node)`` from a ``visit_*`` handler to
        continue recursion into a node's children after custom processing.

        Args:
            node: Any protobuf ``Message`` instance.
        """
        for _field_name, child in _iter_children(node):
            self.visit(child)
