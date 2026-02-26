"""Tree walking and visitor pattern for protobuf parse trees."""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

if TYPE_CHECKING:
    from collections.abc import Generator

    from postgast.nodes.base import AstNode

_NODE_ONEOF = "node"


def unwrap_node(node: Message) -> Message:
    """If *node* is a ``Node`` oneof wrapper, return the inner concrete message; otherwise return *node* unchanged.

    In libpg_query's protobuf schema every child reference is wrapped in a generic ``Node`` message that contains a
    single ``oneof node`` field.  This helper peels that wrapper so you can work with the concrete message type
    (``SelectStmt``, ``ColumnRef``, etc.) directly.

    If *node* is already a concrete message (not a ``Node`` wrapper), it is returned as-is, making this safe to call
    unconditionally.

    Args:
        node: Any protobuf ``Message`` — typically a ``pg_query_pb2.Node``, but concrete messages are accepted too.

    Returns:
        The inner concrete message if *node* was a ``Node`` wrapper, otherwise *node* itself.

    Example:
        >>> from postgast import parse
        >>> from postgast.walk import unwrap_node
        >>> tree = parse("SELECT 1")
        >>> raw_stmt = tree.stmts[0]
        >>> # raw_stmt.stmt is a Node wrapper — unwrap to get the SelectStmt
        >>> select = unwrap_node(raw_stmt.stmt)
        >>> type(select).__name__
        'SelectStmt'
    """
    oneofs = type(node).DESCRIPTOR.oneofs
    if len(oneofs) == 1 and oneofs[0].name == _NODE_ONEOF:
        which = node.WhichOneof(_NODE_ONEOF)
        if which is not None:
            return getattr(node, which)
    return node


def _iter_children(node: Message) -> Generator[tuple[str, Message], None, None]:
    """Yield ``(field_name, child_message)`` for every message-typed field on *node*, unwrapping ``Node`` wrappers."""
    for fd, value in node.ListFields():
        if fd.type != FieldDescriptor.TYPE_MESSAGE:
            continue
        if isinstance(value, Message):
            yield fd.name, unwrap_node(value)
        else:
            for item in value:
                yield fd.name, unwrap_node(item)


def walk(node: Message) -> Generator[tuple[str, Message], None, None]:
    """Depth-first pre-order traversal of a protobuf message tree.

    Yields ``(field_name, message)`` tuples for every protobuf message encountered. The *field_name* is the protobuf
    field name that led to the message (e.g. ``"where_clause"``, ``"target_list"``), or an empty string for the root.

    ``Node`` oneof wrappers are transparently unwrapped so that only concrete message types appear in the output.

    Args:
        node: Any protobuf ``Message`` instance (``ParseResult``, ``SelectStmt``, etc.).

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
        ival: Integer
    """
    node = unwrap_node(node)
    yield "", node
    stack: list[tuple[str, Message]] = list(reversed(list(_iter_children(node))))
    while stack:
        field_name, child = stack.pop()
        yield field_name, child
        stack.extend(reversed(list(_iter_children(child))))


def walk_typed(node: AstNode) -> Generator[tuple[str, AstNode], None, None]:
    """Depth-first pre-order traversal of a typed AST wrapper tree.

    Like :func:`walk` but accepts and yields typed :class:`AstNode` wrappers instead of raw protobuf ``Message``
    objects. Delegates to :func:`walk` internally.

    Args:
        node: A typed ``AstNode`` wrapper (e.g. from :func:`postgast.wrap`).

    Yields:
        ``(field_name, wrapper)`` tuples in depth-first pre-order.

    Example:
        >>> from postgast import parse, wrap, walk_typed
        >>> tree = wrap(parse("SELECT 1"))
        >>> for field_name, node in walk_typed(tree):
        ...     if field_name:
        ...         print(f"{field_name}: {type(node).__name__}")
        stmts: RawStmt
        stmt: SelectStmt
        target_list: ResTarget
        val: A_Const
        ival: Integer
    """
    from postgast.nodes.base import _wrap  # pyright: ignore[reportPrivateUsage]

    for field_name, message in walk(node._pb):  # pyright: ignore[reportPrivateUsage]
        yield field_name, _wrap(message)


class Visitor:
    """Base class for protobuf parse tree visitors.

    Subclass and override ``visit_<TypeName>`` methods (e.g. ``visit_SelectStmt``, ``visit_ColumnRef``) to handle
    specific node types. Unhandled types fall through to :meth:`generic_visit` which recurses into children.

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

        Looks up a method named ``visit_<TypeName>`` (where ``<TypeName>`` matches the protobuf descriptor name, e.g.
        ``visit_SelectStmt``). Falls back to :meth:`generic_visit` if no specific handler exists.

        Args:
            node: Any protobuf ``Message`` instance.
        """
        node = unwrap_node(node)
        type_name = type(node).DESCRIPTOR.name
        handler = getattr(self, f"visit_{type_name}", self.generic_visit)
        handler(node)

    def generic_visit(self, node: Message) -> None:
        """Visit all message-typed children of *node*.

        Override this method to customize the default traversal behavior. Call ``super().generic_visit(node)`` from a
        ``visit_*`` handler to continue recursion into a node's children after custom processing.

        Args:
            node: Any protobuf ``Message`` instance.
        """
        for _field_name, child in _iter_children(node):
            self.visit(child)


class TypedVisitor:
    """Base class for typed AST wrapper visitors.

    Like :class:`Visitor` but dispatches to handlers that receive typed :class:`AstNode` wrappers instead of raw
    protobuf ``Message`` objects.

    Subclass and override ``visit_<TypeName>`` methods to handle specific node types with full type safety::

        class TableCollector(TypedVisitor):
            def __init__(self):
                self.tables = []

            def visit_RangeVar(self, node):
                self.tables.append(node.relname)


        collector = TableCollector()
        collector.visit(wrap(parse_result))
    """

    def visit(self, node: AstNode) -> None:
        """Dispatch *node* to ``visit_<TypeName>`` or :meth:`generic_visit`."""
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        visitor(node)

    def generic_visit(self, node: AstNode) -> None:
        """Visit all child nodes of *node*.

        Override this method to customize the default traversal behavior. Call ``super().generic_visit(node)`` from a
        ``visit_*`` handler to continue recursion into a node's children after custom processing.
        """
        from postgast.nodes.base import _wrap  # pyright: ignore[reportPrivateUsage]

        for _field_name, child in _iter_children(node._pb):  # pyright: ignore[reportPrivateUsage]
            self.visit(_wrap(child))
