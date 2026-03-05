"""SQL pretty-printer that walks the protobuf AST and emits formatted SQL."""

from postgast.format.formatter import format_sql

__all__ = ["format_sql"]
