"""Low-level ctypes bindings to libpg_query.

This module loads the libpg_query shared library via ctypes, defines C struct
bindings for all result types, and declares function signatures. It is an
internal module — use the public postgast API instead.
"""

import ctypes
import ctypes.util
import platform
from ctypes import POINTER, Structure, c_char_p, c_int, c_size_t, c_uint64, c_void_p
from pathlib import Path

_VENDORED_LIB_NAMES = {
    "Linux": "libpg_query.so",
    "Darwin": "libpg_query.dylib",
    "Windows": "pg_query.dll",
}


def _load_libpg_query() -> ctypes.CDLL:
    """Load the libpg_query shared library.

    Checks for a vendored copy bundled alongside this module first, then falls
    back to ctypes.util.find_library for system-installed libraries.

    Returns:
        The loaded CDLL instance.

    Raises:
        OSError: If libpg_query cannot be found via either method.
    """
    # 1. Try vendored library adjacent to this file.
    lib_name = _VENDORED_LIB_NAMES.get(platform.system())
    if lib_name is not None:
        vendored = Path(__file__).parent / lib_name
        if vendored.is_file():
            return ctypes.CDLL(str(vendored))

    # 2. Fall back to system library search.
    path = ctypes.util.find_library("pg_query")
    if path is not None:
        return ctypes.CDLL(path)

    raise OSError(
        "libpg_query shared library not found. "
        "Install postgast from a pre-built wheel (pip install postgast) or "
        "install libpg_query and ensure it is on your library search path "
        "(e.g. LD_LIBRARY_PATH on Linux, DYLD_LIBRARY_PATH on macOS)."
    )


# ---------------------------------------------------------------------------
# Struct definitions
# ---------------------------------------------------------------------------


class PgQueryError(Structure):
    """Mirrors the C PgQueryError struct."""

    _fields_ = [
        ("message", c_char_p),
        ("funcname", c_char_p),
        ("filename", c_char_p),
        ("lineno", c_int),
        ("cursorpos", c_int),
        ("context", c_char_p),
    ]


class PgQueryProtobuf(Structure):
    """Mirrors the C PgQueryProtobuf struct (len + data).

    Uses ``c_void_p`` for ``data`` instead of ``c_char_p`` because protobuf
    binary payloads contain embedded null bytes and ``c_char_p`` would
    silently truncate at the first null.
    """

    _fields_ = [
        ("len", c_size_t),
        ("data", c_void_p),
    ]


class PgQueryParseResult(Structure):
    """Result from pg_query_parse (JSON parse tree)."""

    _fields_ = [
        ("parse_tree", c_char_p),
        ("stderr_buffer", c_char_p),
        ("error", POINTER(PgQueryError)),
    ]


class PgQueryProtobufParseResult(Structure):
    """Result from pg_query_parse_protobuf (binary protobuf parse tree)."""

    _fields_ = [
        ("parse_tree", PgQueryProtobuf),
        ("stderr_buffer", c_char_p),
        ("error", POINTER(PgQueryError)),
    ]


class PgQueryNormalizeResult(Structure):
    """Result from pg_query_normalize."""

    _fields_ = [
        ("normalized_query", c_char_p),
        ("error", POINTER(PgQueryError)),
    ]


class PgQueryFingerprintResult(Structure):
    """Result from pg_query_fingerprint."""

    _fields_ = [
        ("fingerprint", c_uint64),
        ("fingerprint_str", c_char_p),
        ("stderr_buffer", c_char_p),
        ("error", POINTER(PgQueryError)),
    ]


class PgQueryScanResult(Structure):
    """Result from pg_query_scan (binary protobuf scan tokens)."""

    _fields_ = [
        ("pbuf", PgQueryProtobuf),
        ("stderr_buffer", c_char_p),
        ("error", POINTER(PgQueryError)),
    ]


class PgQuerySplitStmt(Structure):
    """Mirrors the C PgQuerySplitStmt struct."""

    _fields_ = [
        ("stmt_location", c_int),
        ("stmt_len", c_int),
    ]


class PgQuerySplitResult(Structure):
    """Result from pg_query_split_with_scanner."""

    _fields_ = [
        ("stmts", POINTER(POINTER(PgQuerySplitStmt))),
        ("n_stmts", c_int),
        ("stderr_buffer", c_char_p),
        ("error", POINTER(PgQueryError)),
    ]


class PgQueryDeparseResult(Structure):
    """Result from pg_query_deparse_protobuf."""

    _fields_ = [
        ("query", c_char_p),
        ("error", POINTER(PgQueryError)),
    ]


# ---------------------------------------------------------------------------
# Load library and declare function signatures
# ---------------------------------------------------------------------------

lib = _load_libpg_query()

# -- Core functions --

lib.pg_query_parse.argtypes = [c_char_p]
lib.pg_query_parse.restype = PgQueryParseResult

lib.pg_query_parse_protobuf.argtypes = [c_char_p]
lib.pg_query_parse_protobuf.restype = PgQueryProtobufParseResult

lib.pg_query_normalize.argtypes = [c_char_p]
lib.pg_query_normalize.restype = PgQueryNormalizeResult

lib.pg_query_fingerprint.argtypes = [c_char_p]
lib.pg_query_fingerprint.restype = PgQueryFingerprintResult

lib.pg_query_scan.argtypes = [c_char_p]
lib.pg_query_scan.restype = PgQueryScanResult

lib.pg_query_split_with_scanner.argtypes = [c_char_p]
lib.pg_query_split_with_scanner.restype = PgQuerySplitResult

lib.pg_query_deparse_protobuf.argtypes = [PgQueryProtobuf]
lib.pg_query_deparse_protobuf.restype = PgQueryDeparseResult

# -- Free functions --

lib.pg_query_free_parse_result.argtypes = [PgQueryParseResult]
lib.pg_query_free_parse_result.restype = None

lib.pg_query_free_protobuf_parse_result.argtypes = [PgQueryProtobufParseResult]
lib.pg_query_free_protobuf_parse_result.restype = None

lib.pg_query_free_normalize_result.argtypes = [PgQueryNormalizeResult]
lib.pg_query_free_normalize_result.restype = None

lib.pg_query_free_fingerprint_result.argtypes = [PgQueryFingerprintResult]
lib.pg_query_free_fingerprint_result.restype = None

lib.pg_query_free_scan_result.argtypes = [PgQueryScanResult]
lib.pg_query_free_scan_result.restype = None

lib.pg_query_free_split_result.argtypes = [PgQuerySplitResult]
lib.pg_query_free_split_result.restype = None

lib.pg_query_free_deparse_result.argtypes = [PgQueryDeparseResult]
lib.pg_query_free_deparse_result.restype = None
