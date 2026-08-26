import ast
import importlib.resources
import os
import pathlib
import subprocess
import sys
from typing import cast

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.internal import enum_type_wrapper

from postgast import parse, pg_query_pb2

# The loader publishes DESCRIPTOR_POOL beyond what protoc --python_out emits, so the generated .pyi — the stub type
# checkers see for this module — does not declare it. Reach it through the module namespace rather than hand-editing
# generated output that `make proto` would overwrite.
DESCRIPTOR_POOL: descriptor_pool.DescriptorPool = vars(pg_query_pb2)["DESCRIPTOR_POOL"]

_LOADER_PATH = pathlib.Path(pg_query_pb2.__file__ or "")
_DESCRIPTOR_PATH = _LOADER_PATH.parent / "pg_query.desc"


def _called_names(source: str) -> set[str]:
    """Collect the attribute and function names called anywhere in a module's source."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def _default_pool_file_name(name: str) -> str:
    """Return the name under which ``name`` is registered in the default descriptor pool.

    Raises:
        KeyError: If the default pool holds no file by that name.
    """
    return descriptor_pool.Default().FindFileByName(name).name  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]


def _default_pool_registration(name: str) -> str | None:
    """Return the file name as registered in the default descriptor pool, or None when it is absent."""
    try:
        return _default_pool_file_name(name)
    except KeyError:
        return None


def _pool_from_committed_descriptor() -> descriptor_pool.DescriptorPool:
    """Build a second, independent pool from the same committed descriptor set."""
    pool = descriptor_pool.DescriptorPool()
    file_set = descriptor_pb2.FileDescriptorSet()
    file_set.ParseFromString(_DESCRIPTOR_PATH.read_bytes())
    for file_proto in file_set.file:
        pool.Add(file_proto)  # pyright: ignore[reportUnknownMemberType]
    return pool


def _parse_result_class_from(pool: descriptor_pool.DescriptorPool) -> type[pg_query_pb2.ParseResult]:
    """Build a ``pg_query.ParseResult`` class out of ``pool``."""
    descriptor = pool.FindMessageTypeByName("pg_query.ParseResult")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    return cast(
        "type[pg_query_pb2.ParseResult]",
        message_factory.GetMessageClass(descriptor),  # pyright: ignore[reportUnknownArgumentType]
    )


class TestProtobufModule:
    def test_pg_query_pb2_importable(self):
        from postgast.pg_query_pb2 import ParseResult

        assert ParseResult is not None

    def test_parse_result_has_version_field(self):
        from postgast.pg_query_pb2 import ParseResult

        msg = ParseResult()
        assert hasattr(msg, "version")

    def test_parse_result_has_stmts_field(self):
        from postgast.pg_query_pb2 import ParseResult

        msg = ParseResult()
        assert hasattr(msg, "stmts")
        assert len(msg.stmts) == 0

    def test_loader_is_not_gencode(self):
        """No gencode/runtime version gate may apply to the module, on any protobuf runtime."""
        assert "ValidateProtobufRuntimeVersion" not in _called_names(_LOADER_PATH.read_text())


class TestCommittedDescriptorSet:
    def test_descriptor_ships_alongside_the_package(self):
        assert _DESCRIPTOR_PATH.is_file()

    def test_descriptor_is_readable_via_importlib_resources(self):
        payload = importlib.resources.files("postgast").joinpath("pg_query.desc").read_bytes()
        assert payload == _DESCRIPTOR_PATH.read_bytes()

    def test_descriptor_set_is_self_contained_and_ordered(self):
        file_set = descriptor_pb2.FileDescriptorSet()
        file_set.ParseFromString(_DESCRIPTOR_PATH.read_bytes())
        assert any(f.name == "pg_query.proto" for f in file_set.file)
        seen: set[str] = set()
        for file_proto in file_set.file:
            for dependency in file_proto.dependency:
                assert dependency in seen, f"{file_proto.name} precedes its dependency {dependency}"
            seen.add(file_proto.name)


class TestPublishedSurface:
    def test_every_message_is_published(self):
        for name in pg_query_pb2.DESCRIPTOR.message_types_by_name:
            assert hasattr(pg_query_pb2, name), f"missing message class {name}"

    def test_every_enum_is_published(self):
        for name in pg_query_pb2.DESCRIPTOR.enum_types_by_name:
            wrapper = vars(pg_query_pb2).get(name)
            assert isinstance(wrapper, enum_type_wrapper.EnumTypeWrapper), f"missing enum wrapper {name}"

    def test_every_enum_value_is_a_module_constant(self):
        namespace = vars(pg_query_pb2)
        for enum_descriptor in pg_query_pb2.DESCRIPTOR.enum_types_by_name.values():
            for value in enum_descriptor.values:
                assert namespace.get(value.name) == value.number, f"missing enum constant {value.name}"

    def test_enum_constants_resolve_to_schema_numbers(self):
        assert pg_query_pb2.AEXPR_OP == 1
        assert pg_query_pb2.SORTBY_ASC == 2
        assert pg_query_pb2.AT_AddColumn == 1

    def test_enum_wrapper_round_trips_name_and_value(self):
        assert pg_query_pb2.A_Expr_Kind.Name(pg_query_pb2.AEXPR_OP) == "AEXPR_OP"
        assert pg_query_pb2.A_Expr_Kind.Value("AEXPR_OP") == pg_query_pb2.AEXPR_OP
        assert pg_query_pb2.SortByDir.Name(pg_query_pb2.SORTBY_ASC) == "SORTBY_ASC"
        assert pg_query_pb2.SortByDir.Value("SORTBY_ASC") == pg_query_pb2.SORTBY_ASC

    def test_nested_types_are_reachable_on_parent(self):
        table = pg_query_pb2.SummaryResult.Table()
        assert hasattr(table, "name")
        # SummaryResult.Context is a nested enum whose zero value is literally named "None".
        assert pg_query_pb2.SummaryResult.Context.Name(0) == "None"
        assert pg_query_pb2.SummaryResult.Context.Value("Select") > 0


class TestDescriptorPool:
    def test_pool_is_private(self):
        assert DESCRIPTOR_POOL is not descriptor_pool.Default()  # pyright: ignore[reportUnknownMemberType]

    def test_schema_is_absent_from_the_default_pool(self):
        assert _default_pool_registration("pg_query.proto") is None

    def test_pool_resolves_by_fully_qualified_name(self):
        node = DESCRIPTOR_POOL.FindMessageTypeByName("pg_query.Node")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        assert node.name == "Node"  # pyright: ignore[reportUnknownMemberType]

    def test_coexists_with_another_registration_of_the_same_schema(self):
        """Importing postgast must not conflict with pg_query.proto already in the default pool."""
        script = (
            "import pathlib, sys\n"
            "from google.protobuf import descriptor_pb2, descriptor_pool\n"
            "fds = descriptor_pb2.FileDescriptorSet()\n"
            "fds.ParseFromString(pathlib.Path(sys.argv[1]).read_bytes())\n"
            "for f in fds.file:\n"
            "    descriptor_pool.Default().Add(f)\n"
            "import postgast\n"
            "print(postgast.parse('SELECT 1').version)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script, str(_DESCRIPTOR_PATH)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert int(result.stdout.strip()) > 0


class TestPurePythonImplementation:
    def test_imports_without_the_native_protobuf_accelerator(self):
        """The loader must not depend on upb/C++ pool behaviour.

        ``DescriptorPool.Add`` returns the descriptor it registered on the upb and C++ implementations but returns
        None on the pure-Python one, so anything reading its return value works in CI and breaks for users who set
        PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python.
        """
        script = (
            "from google.protobuf.internal import api_implementation\n"
            "import postgast\n"
            "print(api_implementation.Type(), postgast.parse('SELECT 1').version)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python"},
        )
        assert result.returncode == 0, result.stderr
        implementation, version = result.stdout.split()
        assert implementation == "python"
        assert int(version) > 0


class TestWireCompatibility:
    def test_serialized_message_round_trips_through_a_separate_pool(self):
        """Bytes from a loader-built message must parse identically in a class built from a different pool."""
        original = parse("SELECT 1 FROM t WHERE a = 2")
        payload = original.SerializeToString()

        foreign = _parse_result_class_from(_pool_from_committed_descriptor())()
        foreign.ParseFromString(payload)

        assert foreign.SerializeToString() == payload
        assert foreign.version == original.version
        assert len(foreign.stmts) == len(original.stmts)

    def test_parse_returns_the_expected_tree(self):
        result = parse("SELECT 1")
        assert len(result.stmts) == 1
        stmt = result.stmts[0].stmt
        assert stmt.WhichOneof("node") == "select_stmt"
        assert len(stmt.select_stmt.target_list) == 1


class TestProtobufReExport:
    def test_pg_query_pb2_from_postgast(self):
        from postgast import pg_query_pb2

        assert hasattr(pg_query_pb2, "ParseResult")
        assert hasattr(pg_query_pb2, "Node")
        assert hasattr(pg_query_pb2, "SelectStmt")
