"""Module-level constants used by the SQL formatter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import postgast.pg_query_pb2 as pb

if TYPE_CHECKING:
    from collections.abc import Mapping

# ── Window frame bitmask constants (PostgreSQL parsenodes.h) ──────

_FRAMEOPTION_NONDEFAULT: Final = 0x00001
_FRAMEOPTION_RANGE: Final = 0x00002
_FRAMEOPTION_ROWS: Final = 0x00004
_FRAMEOPTION_GROUPS: Final = 0x00008
_FRAMEOPTION_BETWEEN: Final = 0x00010
_FRAMEOPTION_START_UNBOUNDED_PRECEDING: Final = 0x00020
_FRAMEOPTION_END_UNBOUNDED_PRECEDING: Final = 0x00040
_FRAMEOPTION_START_UNBOUNDED_FOLLOWING: Final = 0x00080
_FRAMEOPTION_END_UNBOUNDED_FOLLOWING: Final = 0x00100
_FRAMEOPTION_START_CURRENT_ROW: Final = 0x00200
_FRAMEOPTION_END_CURRENT_ROW: Final = 0x00400
_FRAMEOPTION_START_OFFSET_PRECEDING: Final = 0x00800
_FRAMEOPTION_END_OFFSET_PRECEDING: Final = 0x01000
_FRAMEOPTION_START_OFFSET_FOLLOWING: Final = 0x02000
_FRAMEOPTION_END_OFFSET_FOLLOWING: Final = 0x04000
_FRAMEOPTION_EXCLUDE_CURRENT_ROW: Final = 0x08000
_FRAMEOPTION_EXCLUDE_GROUP: Final = 0x10000
_FRAMEOPTION_EXCLUDE_TIES: Final = 0x20000

#: A mapping of built-in type names to their canonical SQL representations for formatting. Types not in this map are
#: emitted as-is.
_TYPE_MAP: Final[Mapping[str, str]] = {
    "int4": "INTEGER",
    "int8": "BIGINT",
    "int2": "SMALLINT",
    "float4": "REAL",
    "float8": "DOUBLE PRECISION",
    "bool": "BOOLEAN",
    "varchar": "VARCHAR",
    "bpchar": "CHARACTER",
    "numeric": "NUMERIC",
    "text": "TEXT",
    "timestamp": "TIMESTAMP",
    "timestamptz": "TIMESTAMPTZ",
    "date": "DATE",
    "time": "TIME",
    "timetz": "TIMETZ",
    "interval": "INTERVAL",
    "uuid": "UUID",
    "json": "JSON",
    "jsonb": "JSONB",
    "bytea": "BYTEA",
    "xml": "XML",
}

_GROUPING_SET_KW: Final[Mapping[int, str]] = {
    pb.GROUPING_SET_ROLLUP: "ROLLUP(",
    pb.GROUPING_SET_CUBE: "CUBE(",
    pb.GROUPING_SET_SETS: "GROUPING SETS (",
}
