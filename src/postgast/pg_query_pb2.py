"""Protobuf message classes for ``pg_query.proto``, built at import time.

Unlike a typical ``*_pb2.py``, this module is hand-written source rather than ``protoc`` output. The generated input it
consumes is :file:`pg_query.desc` — a serialized ``FileDescriptorSet`` emitted by ``make proto`` from the vendored
``vendor/libpg_query/protobuf/pg_query.proto`` — from which the message classes, enum wrappers, and enum constants are
constructed here using the public ``descriptor_pool``, ``descriptor_pb2``, ``message_factory``, and
``enum_type_wrapper`` APIs.

Avoiding ``protoc`` gencode is the point: gencode opens with a call to
``google.protobuf.runtime_version.ValidateProtobufRuntimeVersion``, which refuses to import on any protobuf runtime
older than the protoc that produced it. That gate couples every postgast release to a protoc version for no benefit —
postgast only needs message classes for a schema it already ships, and the wire format is owned by libpg_query's C
encoder. Building from a descriptor set is not covered by the gate, so the module imports on every protobuf runtime
postgast declares support for, across major versions.

Descriptors are registered in a private :class:`~google.protobuf.descriptor_pool.DescriptorPool` exposed as
``DESCRIPTOR_POOL``, not in the default pool, so postgast can coexist with any other package that registers the same
schema. The module's public surface — every top-level message class, every top-level enum wrapper, every enum value as
an integer constant, and ``DESCRIPTOR`` — matches what ``protoc --python_out`` publishes for this schema, so the
committed :file:`pg_query_pb2.pyi` stays an accurate stub. Imports are underscore-aliased for the same reason gencode
aliases them: the schema owns this namespace, and a future message or enum named ``Path`` must not collide with one.
"""

import importlib.resources as _resources
from pathlib import Path as _Path
from typing import Final as _Final

from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message_factory as _message_factory
from google.protobuf.descriptor import Descriptor as _Descriptor
from google.protobuf.descriptor import FileDescriptor as _FileDescriptor
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

_DESCRIPTOR_FILENAME: _Final = "pg_query.desc"

# The schema's own file within the descriptor set; the set may also carry its transitive imports (``--include_imports``).
_PRIMARY_FILE: _Final = "pg_query.proto"


def _read_descriptor_bytes() -> bytes:
    """Read the committed serialized ``FileDescriptorSet`` shipped alongside this module."""
    if __package__:
        return _resources.files(__package__).joinpath(_DESCRIPTOR_FILENAME).read_bytes()
    # Loaded straight from a file path with no package context (this is how scripts/generate_nodes.py imports the
    # module, to avoid pulling in postgast.__init__ and the nodes package it is generating).
    return (_Path(__file__).parent / _DESCRIPTOR_FILENAME).read_bytes()


def _find_primary_file(pool: _descriptor_pool.DescriptorPool) -> _FileDescriptor:
    """Look up the descriptor for ``pg_query.proto`` in ``pool``.

    ``DescriptorPool`` lookups are untyped in some protobuf runtimes, so the declared return type here is what gives
    callers a known type regardless of which runtime is installed.

    Raises:
        KeyError: If the pool holds no file by that name.
    """
    return pool.FindFileByName(_PRIMARY_FILE)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]


def _build_pool() -> tuple[_descriptor_pool.DescriptorPool, _FileDescriptor]:
    """Build a private descriptor pool from the committed descriptor set.

    Returns:
        The pool, and the file descriptor for ``pg_query.proto`` within it.

    Raises:
        RuntimeError: If the descriptor set does not contain ``pg_query.proto``.
    """
    pool = _descriptor_pool.DescriptorPool()
    file_set = _descriptor_pb2.FileDescriptorSet()
    file_set.ParseFromString(_read_descriptor_bytes())
    # ``--include_imports`` orders the set so that each file's dependencies precede it, so a single pass suffices.
    # ``Add`` is deliberately not read for its return value: the upb and C++ pools return the descriptor they
    # registered, but the pure-Python pool returns None, so the primary file is looked up afterwards instead.
    for file_proto in file_set.file:
        pool.Add(file_proto)  # pyright: ignore[reportUnknownMemberType]
    try:
        primary = _find_primary_file(pool)
    except KeyError as exc:  # pragma: no cover — only reachable if pg_query.desc is built from a renamed schema
        raise RuntimeError(f"{_DESCRIPTOR_FILENAME} does not contain {_PRIMARY_FILE}") from exc
    return pool, primary


DESCRIPTOR_POOL, DESCRIPTOR = _build_pool()


def _attach_nested_types(cls: type, message_descriptor: _Descriptor) -> None:
    """Attach nested message classes and nested enum wrappers to ``cls``, recursively.

    The upb and C++ runtimes attach nested types themselves, so every ``setattr`` here is guarded and becomes a no-op
    on those runtimes. The pure-Python runtime does not: ``message_factory.GetMessageClass`` leaves nested message
    classes unreachable from the parent class. Platforms without a prebuilt protobuf extension (musllinux among them)
    select the pure-Python runtime, so without this pass ``SummaryResult.Table`` would not exist there.
    """
    for nested_descriptor in message_descriptor.nested_types:
        nested_cls = _message_factory.GetMessageClass(nested_descriptor)
        _attach_nested_types(nested_cls, nested_descriptor)
        if not hasattr(cls, nested_descriptor.name):
            setattr(cls, nested_descriptor.name, nested_cls)
    for enum_descriptor in message_descriptor.enum_types:
        if not hasattr(cls, enum_descriptor.name):
            setattr(cls, enum_descriptor.name, _enum_type_wrapper.EnumTypeWrapper(enum_descriptor))


def _publish() -> None:
    """Bind every top-level message, enum, and enum value to a module-level name.

    This mirrors what ``protoc --python_out`` emits. The enum value constants are load-bearing: ``precedence.py`` and
    ``format/constants.py`` read them as ``pb.AEXPR_OP``, ``pb.SORTBY_ASC``, ``pb.AT_AddColumn``, and so on.
    """
    namespace = globals()
    for name, message_descriptor in DESCRIPTOR.message_types_by_name.items():
        message_cls = _message_factory.GetMessageClass(message_descriptor)
        _attach_nested_types(message_cls, message_descriptor)
        namespace[name] = message_cls
    for name, enum_descriptor in DESCRIPTOR.enum_types_by_name.items():
        namespace[name] = _enum_type_wrapper.EnumTypeWrapper(enum_descriptor)
        for value in enum_descriptor.values:
            namespace[value.name] = value.number


_publish()
