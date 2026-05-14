"""Verify ctypes struct definitions and function signatures in native.py match pg_query.h.

Parses the upstream C header and the Python source of native.py, then cross-checks struct
field declarations and function signatures. This is a *source-level* check — it compares
what the developer wrote (not runtime type objects) against the C header, avoiding platform
quirks like ``c_size_t is c_uint64`` on 64-bit systems.

Catches: wrong field order, missing/extra fields, wrong types, wrong function signatures,
and new upstream API that hasn't been accounted for yet.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from postgast import native

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_HEADER_PATH = _PROJECT_ROOT / "vendor" / "libpg_query" / "pg_query.h"
_NATIVE_SRC = Path(native.__file__).read_text()

# ---------------------------------------------------------------------------
# Known ABI-compatible overrides: {("Struct", "field"): ("c_type", "py_type")}
# ---------------------------------------------------------------------------

_FIELD_OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    # c_void_p avoids null-byte truncation for protobuf binary data.
    # Both are pointer-sized — ABI-compatible.
    ("PgQueryProtobuf", "data"): ("char*", "void*"),
}

# ---------------------------------------------------------------------------
# Structs/functions in pg_query.h we intentionally don't bind.
# When upstream adds new API, these sets force an explicit decision:
# either bind it in native.py or add it here with a comment.
# ---------------------------------------------------------------------------

_UNBOUND_STRUCTS: set[str] = {
    "PgQueryIsUtilityResult",
    "PgQueryDeparseCommentsResult",
    "PgQuerySummaryParseResult",
}

_UNBOUND_FUNCTIONS: set[str] = {
    "pg_query_init",  # Deprecated
    "pg_query_exit",  # Optional cleanup, not needed
    "pg_query_normalize_utility",  # Not yet exposed
    "pg_query_parse_opts",  # Parse with options variant
    "pg_query_parse_protobuf_opts",  # Parse protobuf with options variant
    "pg_query_fingerprint_opts",  # Fingerprint with options variant
    "pg_query_deparse_protobuf_opts",  # Deparse with options variant
    "pg_query_deparse_comments_for_query",  # Comment preservation
    "pg_query_is_utility_stmt",  # Utility statement detection
    "pg_query_summary",  # Summary feature
    "pg_query_free_deparse_comments_result",
    "pg_query_free_is_utility_result",
    "pg_query_free_summary_parse_result",
}

# ---------------------------------------------------------------------------
# ctypes name → C canonical type mapping (source-level, not runtime)
# ---------------------------------------------------------------------------

_CTYPES_NAME_TO_C: dict[str, str] = {
    "c_char_p": "char*",
    "c_void_p": "void*",
    "c_int": "int",
    "c_size_t": "size_t",
    "c_uint64": "uint64_t",
    "c_bool": "bool",
}


def _py_type_expr_to_c(expr: str) -> str:
    """Convert a Python ctypes type expression (from source) to C canonical form.

    Examples::

        "c_char_p"                         → "char*"
        "c_uint64"                         → "uint64_t"
        "POINTER(PgQueryError)"            → "PgQueryError*"
        "POINTER(POINTER(PgQuerySplitStmt))" → "PgQuerySplitStmt**"
        "PgQueryProtobuf"                  → "PgQueryProtobuf"
    """
    m = re.match(r"POINTER\((.+)\)", expr)
    if m:
        return _py_type_expr_to_c(m.group(1)) + "*"
    if expr in _CTYPES_NAME_TO_C:
        return _CTYPES_NAME_TO_C[expr]
    return expr  # Struct name — already canonical


# ---------------------------------------------------------------------------
# native.py source parsing
# ---------------------------------------------------------------------------

PyField = tuple[str, str]  # (field_name, ctypes_type_expression)
PyStructs = dict[str, list[PyField]]


def _parse_py_structs(source: str) -> PyStructs:
    """Parse struct ``_fields_`` declarations from native.py source code.

    Returns ``{struct_name: [(field_name, type_expr), ...]}``.
    Uses balanced-parenthesis counting to handle nested types like
    ``POINTER(POINTER(PgQuerySplitStmt))``.
    """
    result: PyStructs = {}
    for class_match in re.finditer(
        r"class\s+(\w+)\(Structure\):.*?_fields_\s*=\s*\[(.*?)\]",
        source,
        re.DOTALL,
    ):
        struct_name = class_match.group(1)
        fields_body = class_match.group(2)
        fields: list[PyField] = []
        # Match the opening of each field tuple: ("field_name",
        for field_match in re.finditer(r'\(\s*"(\w+)"\s*,\s*', fields_body):
            field_name = field_match.group(1)
            # Walk forward from after the comma, counting parens to find the
            # closing ')' of the tuple (depth 0 → -1 transition).
            start = field_match.end()
            depth = 0
            pos = start
            while pos < len(fields_body):
                ch = fields_body[pos]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    if depth == 0:
                        break  # This closes the field tuple
                    depth -= 1
                pos += 1
            type_expr = fields_body[start:pos].strip().rstrip(",").strip()
            fields.append((field_name, type_expr))
        result[struct_name] = fields
    return result


PyFuncSig = tuple[str, list[str]]  # (restype_expr, [argtype_exprs])


def _parse_py_functions(source: str) -> dict[str, PyFuncSig]:
    """Parse function ``argtypes``/``restype`` declarations from native.py source code.

    Returns ``{func_name: (restype_expr, [argtype_expr, ...])}``.
    """
    argtypes: dict[str, list[str]] = {}
    restypes: dict[str, str] = {}

    for m in re.finditer(r"lib\.(pg_query_\w+)\.argtypes\s*=\s*\[([^\]]*)\]", source):
        name = m.group(1)
        args_body = m.group(2).strip()
        if args_body:
            argtypes[name] = [a.strip() for a in args_body.split(",") if a.strip()]
        else:
            argtypes[name] = []

    for m in re.finditer(r"lib\.(pg_query_\w+)\.restype\s*=\s*(\S+)", source):
        name = m.group(1)
        restypes[name] = m.group(2).strip()

    result: dict[str, PyFuncSig] = {}
    for name in argtypes:
        restype = restypes.get(name, "c_int")  # ctypes default restype
        result[name] = (restype, argtypes[name])
    return result


def _py_restype_to_c(expr: str) -> str:
    """Convert a Python restype expression to C canonical form."""
    if expr == "None":
        return "void"
    return _py_type_expr_to_c(expr)


# ---------------------------------------------------------------------------
# C header parsing
# ---------------------------------------------------------------------------

CField = tuple[str, str]  # (field_name, canonical_c_type)
CFuncSig = tuple[str, list[str]]  # (return_type, [param_types])


def _read_header() -> str:
    if not _HEADER_PATH.exists():
        pytest.skip(f"Header not found: {_HEADER_PATH} (git submodule not initialized?)")
    return _HEADER_PATH.read_text()


def _parse_c_type(raw: str) -> str:
    """Normalize a C type string: strip const/struct, collapse whitespace around ``*``."""
    s = raw.strip().replace("const ", "").replace("struct ", "")
    s = re.sub(r"\s*(\*+)\s*", r"\1", s)
    return s.strip()


def _parse_c_structs(header: str) -> dict[str, list[CField]]:
    """Extract ``typedef struct { ... } Name;`` definitions from the header."""
    structs: dict[str, list[CField]] = {}
    for m in re.finditer(r"typedef\s+struct\s*\{([^}]+)\}\s*(\w+)\s*;", header, re.DOTALL):
        body, name = m.group(1), m.group(2)
        fields: list[CField] = []
        for line in body.splitlines():
            line = re.sub(r"//.*$", "", line).strip()
            if not line or not line.endswith(";"):
                continue
            line = line[:-1].strip()
            parts = line.rsplit(None, 1)
            if len(parts) != 2:
                continue
            raw_type, field_name = parts
            while field_name.startswith("*"):
                raw_type += "*"
                field_name = field_name[1:]
            fields.append((field_name, _parse_c_type(raw_type)))
        structs[name] = fields
    return structs


def _parse_c_functions(header: str) -> dict[str, CFuncSig]:
    """Extract ``ReturnType pg_query_*(params);`` declarations from the header."""
    funcs: dict[str, CFuncSig] = {}
    for m in re.finditer(r"^(\w[\w\s]*?)\s+(pg_query_\w+)\(([^)]*)\)\s*;", header, re.MULTILINE):
        ret_raw, name, params_raw = m.group(1), m.group(2), m.group(3).strip()
        ret_type = _parse_c_type(ret_raw)
        if params_raw in ("void", ""):
            param_types: list[str] = []
        else:
            param_types = []
            for p in params_raw.split(","):
                p = p.strip()
                parts = p.rsplit(None, 1)
                if len(parts) != 2:
                    param_types.append(_parse_c_type(p))
                    continue
                raw_type, pname = parts
                while pname.startswith("*"):
                    raw_type += "*"
                    pname = pname[1:]
                param_types.append(_parse_c_type(raw_type))
        funcs[name] = (ret_type, param_types)
    return funcs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def header() -> str:
    return _read_header()


@pytest.fixture(scope="module")
def c_structs(header: str) -> dict[str, list[CField]]:
    return _parse_c_structs(header)


@pytest.fixture(scope="module")
def c_funcs(header: str) -> dict[str, CFuncSig]:
    return _parse_c_functions(header)


@pytest.fixture(scope="module")
def py_structs() -> PyStructs:
    return _parse_py_structs(_NATIVE_SRC)


@pytest.fixture(scope="module")
def py_funcs() -> dict[str, PyFuncSig]:
    return _parse_py_functions(_NATIVE_SRC)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestStructBindings:
    """Verify Python struct definitions match the C header."""

    def test_bound_structs_match_header(
        self,
        c_structs: dict[str, list[CField]],
        py_structs: PyStructs,
    ) -> None:
        errors: list[str] = []

        for py_name, py_fields in sorted(py_structs.items()):
            if py_name not in c_structs:
                errors.append(f"{py_name}: not found in C header")
                continue

            c_fields = c_structs[py_name]

            if len(py_fields) != len(c_fields):
                errors.append(f"{py_name}: field count mismatch (C={len(c_fields)}, Python={len(py_fields)})")

            for i, (c_name, c_type) in enumerate(c_fields):
                if i >= len(py_fields):
                    errors.append(f"{py_name}: missing Python field #{i} ({c_name}: {c_type})")
                    continue

                py_field_name, py_type_expr = py_fields[i]
                py_type = _py_type_expr_to_c(py_type_expr)

                if py_field_name != c_name:
                    errors.append(f"{py_name}[{i}]: name mismatch (C={c_name!r}, Python={py_field_name!r})")

                key = (py_name, c_name)
                if key in _FIELD_OVERRIDES:
                    exp_c, exp_py = _FIELD_OVERRIDES[key]
                    if c_type != exp_c or py_type != exp_py:
                        errors.append(
                            f"{py_name}.{c_name}: override assumption violated "
                            f"(expected C={exp_c!r}/Py={exp_py!r}, got C={c_type!r}/Py={py_type!r})"
                        )
                elif py_type != c_type:
                    errors.append(f"{py_name}.{c_name}: type mismatch (C={c_type!r}, Python={py_type!r})")

            for i in range(len(c_fields), len(py_fields)):
                py_field_name, py_type_expr = py_fields[i]
                errors.append(
                    f"{py_name}: extra Python field #{i} ({py_field_name}: {_py_type_expr_to_c(py_type_expr)})"
                )

        assert not errors, "Struct binding mismatches:\n" + "\n".join(f"  - {e}" for e in errors)

    def test_no_unknown_unbound_structs(self, c_structs: dict[str, list[CField]], py_structs: PyStructs) -> None:
        """Fail if the header defines structs we haven't accounted for."""
        unaccounted = sorted(set(c_structs) - set(py_structs) - _UNBOUND_STRUCTS)
        assert not unaccounted, (
            "New structs in pg_query.h — bind them in native.py or add to "
            "_UNBOUND_STRUCTS:\n" + "\n".join(f"  - {s}" for s in unaccounted)
        )


class TestFunctionBindings:
    """Verify Python function signatures match the C header."""

    def test_bound_functions_match_header(
        self,
        c_funcs: dict[str, CFuncSig],
        py_funcs: dict[str, PyFuncSig],
    ) -> None:
        errors: list[str] = []

        for func_name, (py_restype, py_argtypes) in sorted(py_funcs.items()):
            if func_name not in c_funcs:
                errors.append(f"{func_name}: not found in C header")
                continue

            c_ret, c_params = c_funcs[func_name]

            py_ret = _py_restype_to_c(py_restype)
            if py_ret != c_ret:
                errors.append(f"{func_name}: return type mismatch (C={c_ret!r}, Python={py_ret!r})")

            if len(py_argtypes) != len(c_params):
                errors.append(f"{func_name}: param count mismatch (C={len(c_params)}, Python={len(py_argtypes)})")
                continue

            for j, (c_param, py_param) in enumerate(zip(c_params, py_argtypes)):
                py_p = _py_type_expr_to_c(py_param)
                if py_p != c_param:
                    errors.append(f"{func_name}: param #{j} type mismatch (C={c_param!r}, Python={py_p!r})")

        assert not errors, "Function binding mismatches:\n" + "\n".join(f"  - {e}" for e in errors)

    def test_no_unknown_unbound_functions(
        self,
        c_funcs: dict[str, CFuncSig],
        py_funcs: dict[str, PyFuncSig],
    ) -> None:
        """Fail if the header declares functions we haven't accounted for."""
        unaccounted = sorted(set(c_funcs) - set(py_funcs) - _UNBOUND_FUNCTIONS)
        assert not unaccounted, (
            "New functions in pg_query.h — bind them in native.py or add to "
            "_UNBOUND_FUNCTIONS:\n" + "\n".join(f"  - {f}" for f in unaccounted)
        )
