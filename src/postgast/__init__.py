"""Python bindings to libpg_query via ctypes."""

from postgast import pg_query_pb2
from postgast.deparse import deparse
from postgast.errors import PgQueryError
from postgast.fingerprint import FingerprintResult, fingerprint
from postgast.format import format_sql
from postgast.helpers import (
    FunctionIdentity,
    StatementInfo,
    TriggerIdentity,
    classify_statement,
    ensure_if_exists,
    ensure_if_not_exists,
    ensure_or_replace,
    extract_columns,
    extract_function_identity,
    extract_functions,
    extract_tables,
    extract_trigger_identity,
    find_nodes,
    set_if_exists,
    set_if_not_exists,
    set_or_replace,
    to_drop,
)
from postgast.nodes import AstNode, wrap
from postgast.normalize import normalize
from postgast.parse import parse
from postgast.pg_query_pb2 import ParseResult
from postgast.plpgsql import parse_plpgsql
from postgast.precedence import Assoc, Precedence, Side, needs_parens, precedence_of
from postgast.scan import scan
from postgast.split import split
from postgast.walk import TypedVisitor, Visitor, walk, walk_typed

__all__ = [
    "Assoc",
    "AstNode",
    "classify_statement",
    "deparse",
    "ensure_if_exists",
    "ensure_if_not_exists",
    "ensure_or_replace",
    "extract_columns",
    "extract_function_identity",
    "extract_functions",
    "extract_tables",
    "extract_trigger_identity",
    "find_nodes",
    "fingerprint",
    "FingerprintResult",
    "format_sql",
    "FunctionIdentity",
    "needs_parens",
    "normalize",
    "parse_plpgsql",
    "parse",
    "ParseResult",
    "pg_query_pb2",
    "PgQueryError",
    "precedence_of",
    "Precedence",
    "scan",
    "set_if_exists",
    "set_if_not_exists",
    "set_or_replace",
    "Side",
    "split",
    "StatementInfo",
    "to_drop",
    "TriggerIdentity",
    "TypedVisitor",
    "Visitor",
    "walk_typed",
    "walk",
    "wrap",
]
