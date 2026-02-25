"""Operator precedence levels derived from the PostgreSQL parser grammar.

This module encodes the operator-precedence ladder that PostgreSQL's Bison parser uses to resolve ambiguous
expressions. Precedence is a **compile-time artifact**: it lives in ``%left`` / ``%right`` / ``%nonassoc`` directives
inside ``gram.y`` and is not exposed by any catalog, libpg_query API, or runtime data structure. Because the parse tree
already reflects the correct nesting, this table is only needed when *emitting* SQL (formatting / deparsing) to decide
where parentheses are required.

Source
------
The canonical reference is the precedence block near the top of PostgreSQL's ``gram.y``.
For the PostgreSQL 17 version used by this project:

    https://github.com/postgres/postgres/blob/REL_17_STABLE/src/backend/parser/gram.y

Search for the ``%nonassoc`` / ``%left`` / ``%right`` section (roughly lines 100–160).
The table below is a faithful transcription.

PostgreSQL is Copyright (c) 1996-2025, The PostgreSQL Global Development Group, and is distributed under the PostgreSQL
License. See https://www.postgresql.org/about/licence/ for details.

The precedence table has been extremely stable (the last major rework was in PostgreSQL 9.5 for SQL-standard compliance).
**When upgrading the vendored libpg_query, verify the table still matches.**
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Final, Literal, TypeAlias

import postgast.pg_query_pb2 as pb

if TYPE_CHECKING:
    from collections.abc import Mapping

    from google.protobuf.message import Message


class Assoc(enum.Enum):
    """Operator associativity (mirrors Bison ``%left`` / ``%right`` / ``%nonassoc``)."""

    LEFT = "left"
    RIGHT = "right"
    NONE = "nonassoc"


class Side(enum.Enum):
    """Which side of a binary operator a child expression appears on."""

    LEFT = "left"
    RIGHT = "right"


# ---------------------------------------------------------------------------
# Precedence levels
# ---------------------------------------------------------------------------
#
# Higher numeric value == tighter binding. The numbers are arbitrary; only their relative order matters.  They follow
# the declaration order in gram.y (bottom = tightest).
#
# gram.y (PostgreSQL 17, REL_17_STABLE):
#
#   %left       UNION EXCEPT
#   %left       INTERSECT
#   %left       OR
#   %left       AND
#   %right      NOT
#   %nonassoc   IS ISNULL NOTNULL
#   %nonassoc   '<' '>' '=' LESS_EQUALS GREATER_EQUALS NOT_EQUALS
#   %nonassoc   BETWEEN IN_P LIKE ILIKE SIMILAR NOT_LA
#   %nonassoc   ESCAPE
#   %nonassoc   UNBOUNDED NESTED
#   %nonassoc   IDENT PARTITION RANGE ROWS GROUPS ...
#   %left       Op OPERATOR
#   %left       '+' '-'
#   %left       '*' '/' '%'
#   %left       '^'
#   %left       AT
#   %left       COLLATE
#   %right      UMINUS
#   %left       '[' ']'
#   %left       '(' ')'
#   %left       TYPECAST
#   %left       '.'

UNION: Final = 1
INTERSECT: Final = 2
OR: Final = 3
AND: Final = 4
NOT: Final = 5
IS: Final = 6
COMPARISON: Final = 7
PATTERN: Final = 8  # BETWEEN, IN, LIKE, ILIKE, SIMILAR
ESCAPE: Final = 9
OP: Final = 10  # generic operator / OPERATOR(...)
ADD_SUB: Final = 11  # + -
MUL_DIV: Final = 12  # * / %
EXP: Final = 13  # ^
AT: Final = 14
COLLATE: Final = 15
UMINUS: Final = 16
SUBSCRIPT: Final = 17  # [ ]
PAREN: Final = 18  # ( )
TYPECAST: Final = 19  # ::
DOT: Final = 20  # .

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_Op: TypeAlias = Literal[
    ">", "<", "=", "<=", ">=", "<>", "!=", "+", "-", "*", "/", "%", "^", "||", "&", "|", "#", "~", "<<", ">>"
]
# Maps operator symbol strings to (precedence, associativity).
_OP_TABLE: Final[Mapping[_Op, tuple[int, Assoc]]] = {
    # Comparison operators  (gram.y: '<' '>' '=' LESS_EQUALS ...)
    "<": (COMPARISON, Assoc.NONE),
    ">": (COMPARISON, Assoc.NONE),
    "=": (COMPARISON, Assoc.NONE),
    "<=": (COMPARISON, Assoc.NONE),
    ">=": (COMPARISON, Assoc.NONE),
    "<>": (COMPARISON, Assoc.NONE),
    "!=": (COMPARISON, Assoc.NONE),
    # Additive  (gram.y: '+' '-')
    "+": (ADD_SUB, Assoc.LEFT),
    "-": (ADD_SUB, Assoc.LEFT),
    # Multiplicative  (gram.y: '*' '/' '%')
    "*": (MUL_DIV, Assoc.LEFT),
    "/": (MUL_DIV, Assoc.LEFT),
    "%": (MUL_DIV, Assoc.LEFT),
    # Exponent  (gram.y: '^')
    "^": (EXP, Assoc.LEFT),
    # String concatenation and bitwise ops get generic Op precedence
    "||": (OP, Assoc.LEFT),
    "&": (OP, Assoc.LEFT),
    "|": (OP, Assoc.LEFT),
    "#": (OP, Assoc.LEFT),
    "~": (OP, Assoc.LEFT),
    "<<": (OP, Assoc.LEFT),
    ">>": (OP, Assoc.LEFT),
}


class Precedence:
    """Precedence and associativity for an AST expression node.

    Attributes:
        level: Numeric precedence level (higher = tighter binding).
        assoc: Associativity of the operator.
    """

    __slots__ = ("assoc", "level")

    def __init__(self, level: int, assoc: Assoc) -> None:  # noqa: D107
        self.level = level
        self.assoc = assoc

    def __repr__(self) -> str:  # pyright: ignore[reportImplicitOverride]  # noqa: D105
        return f"Precedence(level={self.level}, assoc={self.assoc!r})"

    def __eq__(self, other: object) -> bool:  # pyright: ignore[reportImplicitOverride]  # noqa: D105
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.level == other.level and self.assoc == other.assoc

    def __hash__(self) -> int:  # pyright: ignore[reportImplicitOverride]  # noqa: D105
        return hash((self.level, self.assoc))


#: Sentinel returned for nodes whose precedence is irrelevant (atomic
#: expressions like column references, constants, function calls, etc.).
#: The level is set higher than any real operator so that atomic nodes
#: never trigger unnecessary parentheses.
ATOMIC: Final = Precedence(level=999, assoc=Assoc.NONE)


def _unwrap_node(node: pb.Node) -> object:
    """Return the concrete message inside a ``Node`` oneof wrapper."""
    field = node.WhichOneof("node")
    if field is None:
        return node
    return getattr(node, field)


def precedence_of(node: pb.Node | Message) -> Precedence:
    """Return the precedence of an expression node.

    Given a protobuf ``Node`` (or an already-unwrapped message), return a ``Precedence`` describing how tightly it
    binds. This is the key building block for deciding whether parentheses are needed when emitting SQL.

    Nodes that are *atomic* (column references, constants, function calls, subselects, etc.) return ``ATOMIC``, a
    sentinel with a very high precedence level so they never require wrapping.

    Args:
        node: A ``pg_query_pb2.Node`` or an unwrapped protobuf message (e.g. ``A_Expr``, ``BoolExpr``).

    Returns:
        A ``Precedence`` with *level* and *assoc* fields.

    Example:
        >>> import postgast.pg_query_pb2 as pb
        >>> from postgast.precedence import precedence_of, AND, OR
        >>> bool_and = pb.BoolExpr(boolop=pb.AND_EXPR)
        >>> precedence_of(bool_and).level == AND
        True
        >>> precedence_of(bool_and).level > OR
        True
    """
    inner = _unwrap_node(node) if isinstance(node, pb.Node) else node

    # -- BoolExpr: NOT > AND > OR --
    if isinstance(inner, pb.BoolExpr):
        if inner.boolop == pb.NOT_EXPR:
            return Precedence(NOT, Assoc.RIGHT)
        if inner.boolop == pb.AND_EXPR:
            return Precedence(AND, Assoc.LEFT)
        return Precedence(OR, Assoc.LEFT)

    # -- A_Expr: depends on kind and operator name --
    if isinstance(inner, pb.A_Expr):
        kind = inner.kind

        if kind == pb.AEXPR_OP:
            # Unary prefix minus gets UMINUS precedence
            if not inner.HasField("lexpr") and inner.name:
                op_node = _unwrap_node(inner.name[0])
                if isinstance(op_node, pb.String) and op_node.sval == "-":
                    return Precedence(UMINUS, Assoc.RIGHT)
            # Binary operator — look up the symbol
            if inner.name:
                op_name_node = _unwrap_node(inner.name[0])
                if isinstance(op_name_node, pb.String):
                    sym = op_name_node.sval
                    if sym in _OP_TABLE:
                        level, assoc = _OP_TABLE[sym]
                        return Precedence(level, assoc)
            # Unknown / user-defined operator → generic Op precedence
            return Precedence(OP, Assoc.LEFT)

        if kind in (pb.AEXPR_LIKE, pb.AEXPR_ILIKE, pb.AEXPR_SIMILAR):
            return Precedence(PATTERN, Assoc.NONE)

        if kind in (pb.AEXPR_BETWEEN, pb.AEXPR_NOT_BETWEEN, pb.AEXPR_BETWEEN_SYM, pb.AEXPR_NOT_BETWEEN_SYM):
            return Precedence(PATTERN, Assoc.NONE)

        if kind == pb.AEXPR_IN:
            return Precedence(PATTERN, Assoc.NONE)

        if kind in (pb.AEXPR_OP_ANY, pb.AEXPR_OP_ALL):
            return Precedence(PATTERN, Assoc.NONE)

        if kind in (pb.AEXPR_DISTINCT, pb.AEXPR_NOT_DISTINCT, pb.AEXPR_NULLIF):
            return ATOMIC

        # Fallback for any future A_Expr kinds
        return Precedence(OP, Assoc.LEFT)

    # -- NullTest: IS NULL / IS NOT NULL — same level as IS --
    if isinstance(inner, pb.NullTest):
        return Precedence(IS, Assoc.NONE)

    # -- BooleanTest: IS TRUE / IS FALSE / etc. — same level as IS --
    if isinstance(inner, pb.BooleanTest):
        return Precedence(IS, Assoc.NONE)

    # -- TypeCast (::) --
    if isinstance(inner, pb.TypeCast):
        return Precedence(TYPECAST, Assoc.LEFT)

    # -- Everything else is atomic --
    return ATOMIC


def needs_parens(parent: pb.Node | Message, child: pb.Node | Message, *, side: Side | None = None) -> bool:
    """Decide whether *child* needs parentheses when nested inside *parent*.

    This encodes the fundamental rule:

    * If the child binds **less tightly** than the parent, it needs parens.
    * If they bind **equally** and the parent is ``nonassoc``, the child always needs parens
      (PostgreSQL rejects ``a = b = c``).
    * If they bind **equally** and *side* is provided, associativity is checked: a child on the non-associative side of
      a left- or right-associative parent needs parens (e.g. the right operand of ``a - (b + c)``).
    * If they bind **equally**, the parent is left/right-associative, and *side* is ``None``, parens are **not** added
      (conservative default that avoids false positives when side information is unavailable).

    Args:
        parent: The outer expression node.
        child: The inner expression node to test.
        side: Which side of *parent* the *child* appears on. When provided, enables associativity-aware decisions for
              equal-precedence operators.

    Returns:
        ``True`` if the child should be wrapped in ``(``, ``)``.

    Example:
        >>> import postgast.pg_query_pb2 as pb
        >>> from postgast.precedence import needs_parens, Side
        >>> or_expr = pb.BoolExpr(boolop=pb.OR_EXPR)
        >>> and_expr = pb.BoolExpr(boolop=pb.AND_EXPR)
        >>> needs_parens(and_expr, or_expr)
        True
        >>> needs_parens(or_expr, and_expr)
        False
    """
    p = precedence_of(parent)
    c = precedence_of(child)

    # If the child binds less tightly than the parent, it needs parens.
    if c.level < p.level:
        return True

    # If the child binds more tightly, it doesn't need parens.
    if c.level != p.level:
        return False

    # Equal precedence: decision depends on associativity.
    if p.assoc is Assoc.NONE:
        return True

    if side is None:
        return False

    # Left-associative: right child at same level needs parens (a - (b + c))
    if p.assoc is Assoc.LEFT:
        return side is Side.RIGHT

    # Right-associative: left child at same level needs parens
    return side is Side.LEFT
