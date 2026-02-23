#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["postgast"]
# ///
"""Generate typed AST wrapper classes from the protobuf descriptor.

Usage:
    uv run scripts/generate_nodes.py

Writes to src/postgast/nodes.py. The output is checked into version control.
"""

from __future__ import annotations

import importlib.util
import keyword
import textwrap
from pathlib import Path

from google.protobuf.descriptor import Descriptor, FieldDescriptor

# Load pg_query_pb2 directly from file to avoid triggering postgast.__init__
# (which imports nodes.py — the file we're generating)
_PB2_PATH = Path(__file__).resolve().parent.parent / "src" / "postgast" / "pg_query_pb2.py"
_spec = importlib.util.spec_from_file_location("pg_query_pb2", _PB2_PATH)
assert _spec is not None and _spec.loader is not None
pg_query_pb2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg_query_pb2)

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "src" / "postgast" / "nodes.py"

# Protobuf type constants
_TYPE_MESSAGE = FieldDescriptor.TYPE_MESSAGE
_TYPE_ENUM = FieldDescriptor.TYPE_ENUM
_TYPE_STRING = FieldDescriptor.TYPE_STRING
_TYPE_BOOL = FieldDescriptor.TYPE_BOOL
_TYPE_INT32 = FieldDescriptor.TYPE_INT32
_TYPE_INT64 = FieldDescriptor.TYPE_INT64
_TYPE_UINT32 = FieldDescriptor.TYPE_UINT32
_TYPE_UINT64 = FieldDescriptor.TYPE_UINT64
_TYPE_FLOAT = FieldDescriptor.TYPE_FLOAT
_TYPE_DOUBLE = FieldDescriptor.TYPE_DOUBLE
_LABEL_REPEATED = FieldDescriptor.LABEL_REPEATED

# Types to skip in __match_args__ (internal/location fields)
_SKIP_MATCH_FIELDS = {"location", "stmt_location", "stmt_len"}

# Map protobuf scalar types to Python type annotation strings
_SCALAR_TYPE_MAP: dict[int, str] = {
    _TYPE_STRING: "str",
    _TYPE_BOOL: "bool",
    _TYPE_INT32: "int",
    _TYPE_INT64: "int",
    _TYPE_UINT32: "int",
    _TYPE_UINT64: "int",
    _TYPE_FLOAT: "float",
    _TYPE_DOUBLE: "float",
}


def _is_node_oneof(desc: Descriptor) -> bool:
    """Check if a message descriptor is the Node oneof wrapper."""
    return len(desc.oneofs) == 1 and desc.oneofs[0].name == "node"


def _get_non_node_oneofs(desc: Descriptor) -> list[tuple[str, list[FieldDescriptor]]]:
    """Get oneofs that are NOT the Node wrapper (e.g., A_Const.val)."""
    result = []
    for oneof in desc.oneofs:
        if oneof.name != "node":
            result.append((oneof.name, list(oneof.fields)))
    return result


def _safe_name(name: str) -> str:
    """Append underscore to Python keywords to make valid identifiers."""
    if keyword.iskeyword(name):
        return name + "_"
    return name


def _wrapper_name(msg_desc: Descriptor) -> str:
    """Return the wrapper class name, using underscored parent prefix for nested types."""
    if msg_desc.containing_type is not None:
        return f"{msg_desc.containing_type.name}_{msg_desc.name}"
    return msg_desc.name


def _field_python_type(fd: FieldDescriptor) -> str:
    """Return the Python type annotation for a field."""
    if fd.type == _TYPE_MESSAGE:
        if _is_node_oneof(fd.message_type):
            # Node oneof wrapper -> unwrap to AstNode
            if fd.is_repeated:
                return "list[AstNode]"
            return "AstNode | None"
        # Concrete message type
        wrapper = _wrapper_name(fd.message_type)
        if fd.is_repeated:
            return f"list[{wrapper}]"
        return f"{wrapper} | None"
    # Scalar/enum types
    scalar = _SCALAR_TYPE_MAP.get(fd.type)
    if scalar is None:
        scalar = "int"  # enums and other integer types
    if fd.is_repeated:
        return f"list[{scalar}]"
    return scalar


def _pb_attr(name: str) -> str:
    """Return the expression for accessing a protobuf field, using getattr for keywords."""
    if keyword.iskeyword(name):
        return f'getattr(self._pb, "{name}")'
    return f"self._pb.{name}"


def _field_body(fd: FieldDescriptor) -> str:
    """Return the property body for a field."""
    name = fd.name
    attr = _pb_attr(name)
    if fd.type == _TYPE_MESSAGE:
        wrapper = _wrapper_name(fd.message_type)
        if _is_node_oneof(fd.message_type):
            if fd.is_repeated:
                return f"return _wrap_list({attr})"
            return f"return _wrap_node_optional({attr})"
        if fd.is_repeated:
            return f"return [{wrapper}(item) for item in {attr}]"
        return f"return {wrapper}({attr}) if self._pb.HasField({name!r}) else None"
    # Scalar or enum
    if fd.is_repeated:
        return f"return list({attr})"
    return f"return {attr}"


def _generate_oneof_property(oneof_name: str, oneof_fields: list[FieldDescriptor]) -> str:
    """Generate a property for a non-Node oneof (like A_Const.val)."""
    lines = []
    lines.append("    @property")
    lines.append(f"    def {oneof_name}(self) -> AstNode | int | float | bool | str | None:")
    lines.append(f"        which = self._pb.WhichOneof({oneof_name!r})")
    lines.append("        if which is None:")
    lines.append("            return None")
    lines.append("        inner = getattr(self._pb, which)")
    # If all oneof fields are messages, wrap them
    all_messages = all(f.type == _TYPE_MESSAGE for f in oneof_fields)
    if all_messages:
        lines.append("        return _wrap(inner)")
    else:
        lines.append("        return inner")
    return "\n".join(lines)


def _pb_type_name(desc: Descriptor) -> str:
    """Return the pg_query_pb2 type reference for a descriptor."""
    if desc.containing_type is not None:
        return f"pg_query_pb2.{desc.containing_type.name}.{desc.name}"
    return f"pg_query_pb2.{desc.name}"


def _generate_class(desc: Descriptor) -> str:
    """Generate a wrapper class for a message type."""
    name = _wrapper_name(desc)
    pb_type = _pb_type_name(desc)
    lines = []
    lines.append(f"class {name}(AstNode):")
    lines.append("    __slots__ = ()")
    lines.append(f"    _pb: {pb_type}")

    # Collect fields NOT part of a non-Node oneof
    non_node_oneofs = _get_non_node_oneofs(desc)
    oneof_field_names = set()
    for _, fields in non_node_oneofs:
        for f in fields:
            oneof_field_names.add(f.name)

    # Regular fields (not part of custom oneofs)
    regular_fields = [f for f in desc.fields if f.name not in oneof_field_names]

    # __match_args__: non-location fields
    match_fields = []
    for fd in regular_fields:
        if fd.name not in _SKIP_MATCH_FIELDS:
            match_fields.append(_safe_name(fd.name))
    for oneof_name, _ in non_node_oneofs:
        match_fields.append(oneof_name)
    if match_fields:
        match_str = ", ".join(f'"{f}"' for f in match_fields)
        lines.append(f"    __match_args__ = ({match_str},)")
    else:
        lines.append("    __match_args__ = ()")

    # Regular field properties
    for fd in regular_fields:
        ptype = _field_python_type(fd)
        body = _field_body(fd)
        prop_name = _safe_name(fd.name)
        lines.append("")
        lines.append("    @property")
        lines.append(f"    def {prop_name}(self) -> {ptype}:")
        lines.append(f"        {body}")

    # Oneof properties (like A_Const.val)
    for oneof_name, oneof_fields in non_node_oneofs:
        lines.append("")
        lines.append(_generate_oneof_property(oneof_name, oneof_fields))

    # If no fields at all, add pass
    if not regular_fields and not non_node_oneofs:
        lines.append("    pass")

    return "\n".join(lines)


def generate() -> str:
    """Generate the complete nodes.py content."""
    descriptor = pg_query_pb2.DESCRIPTOR

    parts: list[str] = []

    # Header
    parts.append(
        textwrap.dedent("""\
        # DO NOT EDIT — generated by scripts/generate_nodes.py
        # ruff: noqa: D100,D101,D102,D105,D107,PIE790
        #
        # Typed AST wrapper classes for all protobuf node types.
        # Regenerate with: uv run python scripts/generate_nodes.py

        from __future__ import annotations

        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from collections.abc import Iterable

            from google.protobuf.message import Message

            import postgast.pg_query_pb2 as pg_query_pb2
    """)
    )

    # AstNode base class
    parts.append(
        textwrap.dedent("""\

        class AstNode:
            \"\"\"Base class for all typed AST wrappers.\"\"\"

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
    """)
    )

    # Collect all message descriptors (including nested types)
    all_descs: list[Descriptor] = []
    for name in sorted(descriptor.message_types_by_name):
        msg_desc = descriptor.message_types_by_name[name]
        if _is_node_oneof(msg_desc):
            continue
        all_descs.append(msg_desc)
        for nested in msg_desc.nested_types:
            all_descs.append(nested)

    # Generate all wrapper classes
    for desc in all_descs:
        parts.append("")
        parts.append("")
        parts.append(_generate_class(desc))

    # Registry (maps descriptor name to wrapper class)
    parts.append("")
    parts.append("")
    registry_entries = []
    for desc in all_descs:
        wrapper = _wrapper_name(desc)
        registry_entries.append(f'    "{desc.name}": {wrapper},')
    parts.append("_REGISTRY: dict[str, type[AstNode]] = {")
    for entry in registry_entries:
        parts.append(entry)
    parts.append("}")

    # Helper functions
    parts.append(
        textwrap.dedent("""

        def _wrap(pb: Message) -> AstNode:
            \"\"\"Wrap a protobuf message in its typed AST wrapper.\"\"\"
            desc = type(pb).DESCRIPTOR
            # Unwrap Node oneof if needed
            if len(desc.oneofs) == 1 and desc.oneofs[0].name == "node":
                which = pb.WhichOneof("node")
                if which is not None:
                    pb = getattr(pb, which)
            cls = _REGISTRY.get(type(pb).DESCRIPTOR.name, AstNode)
            return cls(pb)


        def _wrap_node_optional(pb: Message) -> AstNode | None:
            \"\"\"Wrap a Node oneof field, returning None if unset.\"\"\"
            which = pb.WhichOneof("node")
            if which is None:
                return None
            inner = getattr(pb, which)
            cls = _REGISTRY.get(type(inner).DESCRIPTOR.name, AstNode)
            return cls(inner)


        def _wrap_list(repeated: Iterable[Message]) -> list[AstNode]:
            \"\"\"Wrap a repeated Node field into a list of typed wrappers.\"\"\"
            result: list[AstNode] = []
            for item in repeated:
                which = item.WhichOneof("node")
                if which is not None:
                    inner = getattr(item, which)
                    cls = _REGISTRY.get(type(inner).DESCRIPTOR.name, AstNode)
                    result.append(cls(inner))
            return result


        def wrap(tree: Message) -> AstNode:
            \"\"\"Wrap a protobuf message tree in typed AST wrappers.

            This is the main entry point. Pass a ``ParseResult`` from
            ``postgast.parse()`` to get a fully typed wrapper tree.

            Args:
                tree: Any protobuf ``Message`` (typically ``ParseResult``).

            Returns:
                A typed ``AstNode`` wrapper. Access fields as properties;
                nested nodes are wrapped lazily on access.

            Example:
                >>> from postgast import parse
                >>> from postgast.nodes import wrap, SelectStmt
                >>> tree = wrap(parse("SELECT 1"))
                >>> stmt = tree.stmts[0].stmt
                >>> isinstance(stmt, SelectStmt)
                True
            \"\"\"
            if isinstance(tree, AstNode):
                return tree
            return _wrap(tree)
    """)
    )

    return "\n".join(parts)


def main() -> None:
    content = generate()
    OUTPUT_PATH.write_text(content)

    # Format with ruff
    import subprocess

    subprocess.run(["ruff", "format", str(OUTPUT_PATH)], check=True)

    # Count classes
    formatted = OUTPUT_PATH.read_text()
    class_count = formatted.count("\nclass ") - 1  # subtract AstNode base class
    print(f"Generated {OUTPUT_PATH}")
    print(f"  {class_count} wrapper classes")


if __name__ == "__main__":
    main()
