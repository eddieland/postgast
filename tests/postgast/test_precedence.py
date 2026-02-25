"""Tests for the operator precedence module."""

from __future__ import annotations

import postgast.pg_query_pb2 as pb
from postgast.precedence import (
    ADD_SUB,
    AND,
    ATOMIC,
    COMPARISON,
    EXP,
    IS,
    MUL_DIV,
    NOT,
    OP,
    OR,
    PATTERN,
    TYPECAST,
    UMINUS,
    Assoc,
    Precedence,
    needs_parens,
    precedence_of,
)


class TestBoolExprPrecedence:
    def test_or(self):
        p = precedence_of(pb.BoolExpr(boolop=pb.OR_EXPR))
        assert p.level == OR
        assert p.assoc is Assoc.LEFT

    def test_and(self):
        p = precedence_of(pb.BoolExpr(boolop=pb.AND_EXPR))
        assert p.level == AND
        assert p.assoc is Assoc.LEFT

    def test_not(self):
        p = precedence_of(pb.BoolExpr(boolop=pb.NOT_EXPR))
        assert p.level == NOT
        assert p.assoc is Assoc.RIGHT

    def test_ordering_not_gt_and_gt_or(self):
        assert NOT > AND > OR


def _make_a_expr(op: str, kind: int = pb.AEXPR_OP, *, unary: bool = False) -> pb.A_Expr:
    """Build a minimal A_Expr node with the given operator."""
    name_node = pb.Node(string=pb.String(sval=op))
    expr = pb.A_Expr(
        kind=kind,  # pyright: ignore[reportArgumentType]
        name=[name_node],
    )
    if not unary:
        expr.lexpr.CopyFrom(
            pb.Node(
                column_ref=pb.ColumnRef(
                    fields=[
                        pb.Node(string=pb.String(sval="a")),
                    ],
                ),
            ),
        )
    expr.rexpr.CopyFrom(
        pb.Node(
            column_ref=pb.ColumnRef(
                fields=[
                    pb.Node(string=pb.String(sval="b")),
                ],
            ),
        ),
    )
    return expr


class TestAExprPrecedence:
    def test_plus(self):
        p = precedence_of(_make_a_expr("+"))
        assert p.level == ADD_SUB
        assert p.assoc is Assoc.LEFT

    def test_minus(self):
        p = precedence_of(_make_a_expr("-"))
        assert p.level == ADD_SUB

    def test_multiply(self):
        p = precedence_of(_make_a_expr("*"))
        assert p.level == MUL_DIV

    def test_divide(self):
        p = precedence_of(_make_a_expr("/"))
        assert p.level == MUL_DIV

    def test_modulo(self):
        p = precedence_of(_make_a_expr("%"))
        assert p.level == MUL_DIV

    def test_exponent(self):
        p = precedence_of(_make_a_expr("^"))
        assert p.level == EXP

    def test_equals(self):
        p = precedence_of(_make_a_expr("="))
        assert p.level == COMPARISON
        assert p.assoc is Assoc.NONE

    def test_not_equals(self):
        assert precedence_of(_make_a_expr("<>")).level == COMPARISON
        assert precedence_of(_make_a_expr("!=")).level == COMPARISON

    def test_less_than(self):
        assert precedence_of(_make_a_expr("<")).level == COMPARISON

    def test_greater_than(self):
        assert precedence_of(_make_a_expr(">")).level == COMPARISON

    def test_less_equals(self):
        assert precedence_of(_make_a_expr("<=")).level == COMPARISON

    def test_greater_equals(self):
        assert precedence_of(_make_a_expr(">=")).level == COMPARISON

    def test_concat(self):
        p = precedence_of(_make_a_expr("||"))
        assert p.level == OP

    def test_unknown_operator_gets_generic_op(self):
        p = precedence_of(_make_a_expr("@>"))
        assert p.level == OP
        assert p.assoc is Assoc.LEFT

    def test_ordering_mul_gt_add_gt_comparison(self):
        assert MUL_DIV > ADD_SUB > COMPARISON

    def test_ordering_exp_gt_mul(self):
        assert EXP > MUL_DIV

    def test_ordering_comparison_gt_and(self):
        assert COMPARISON > AND


class TestUnaryMinus:
    def test_unary_minus_precedence(self):
        p = precedence_of(_make_a_expr("-", unary=True))
        assert p.level == UMINUS
        assert p.assoc is Assoc.RIGHT

    def test_unary_minus_tighter_than_binary(self):
        assert UMINUS > MUL_DIV


class TestAExprKindPrecedence:
    def test_like(self):
        p = precedence_of(_make_a_expr("~~", kind=pb.AEXPR_LIKE))
        assert p.level == PATTERN

    def test_ilike(self):
        p = precedence_of(_make_a_expr("~~*", kind=pb.AEXPR_ILIKE))
        assert p.level == PATTERN

    def test_similar(self):
        p = precedence_of(_make_a_expr("~", kind=pb.AEXPR_SIMILAR))
        assert p.level == PATTERN

    def test_between(self):
        expr = pb.A_Expr(kind=pb.AEXPR_BETWEEN)
        assert precedence_of(expr).level == PATTERN

    def test_not_between(self):
        expr = pb.A_Expr(kind=pb.AEXPR_NOT_BETWEEN)
        assert precedence_of(expr).level == PATTERN

    def test_in(self):
        expr = pb.A_Expr(kind=pb.AEXPR_IN)
        assert precedence_of(expr).level == PATTERN

    def test_op_any(self):
        expr = pb.A_Expr(kind=pb.AEXPR_OP_ANY)
        assert precedence_of(expr).level == PATTERN

    def test_op_all(self):
        expr = pb.A_Expr(kind=pb.AEXPR_OP_ALL)
        assert precedence_of(expr).level == PATTERN

    def test_distinct_is_atomic(self):
        expr = pb.A_Expr(kind=pb.AEXPR_DISTINCT)
        assert precedence_of(expr) == ATOMIC

    def test_nullif_is_atomic(self):
        expr = pb.A_Expr(kind=pb.AEXPR_NULLIF)
        assert precedence_of(expr) == ATOMIC


class TestOtherNodePrecedence:
    def test_null_test(self):
        p = precedence_of(pb.NullTest())
        assert p.level == IS

    def test_boolean_test(self):
        p = precedence_of(pb.BooleanTest())
        assert p.level == IS

    def test_typecast(self):
        p = precedence_of(pb.TypeCast())
        assert p.level == TYPECAST
        assert p.assoc is Assoc.LEFT

    def test_column_ref_is_atomic(self):
        assert precedence_of(pb.ColumnRef()) == ATOMIC

    def test_a_const_is_atomic(self):
        assert precedence_of(pb.A_Const()) == ATOMIC

    def test_func_call_is_atomic(self):
        assert precedence_of(pb.FuncCall()) == ATOMIC

    def test_sub_link_is_atomic(self):
        assert precedence_of(pb.SubLink()) == ATOMIC

    def test_case_expr_is_atomic(self):
        assert precedence_of(pb.CaseExpr()) == ATOMIC


class TestNodeWrapped:
    def test_bool_expr_in_node(self):
        node = pb.Node(bool_expr=pb.BoolExpr(boolop=pb.AND_EXPR))
        assert precedence_of(node).level == AND

    def test_a_expr_in_node(self):
        inner = _make_a_expr("+")
        node = pb.Node(a_expr=inner)
        assert precedence_of(node).level == ADD_SUB

    def test_column_ref_in_node(self):
        node = pb.Node(column_ref=pb.ColumnRef())
        assert precedence_of(node) == ATOMIC


class TestNeedsParens:
    def test_or_inside_and_needs_parens(self):
        parent = pb.BoolExpr(boolop=pb.AND_EXPR)
        child = pb.BoolExpr(boolop=pb.OR_EXPR)
        assert needs_parens(parent, child) is True

    def test_and_inside_or_no_parens(self):
        parent = pb.BoolExpr(boolop=pb.OR_EXPR)
        child = pb.BoolExpr(boolop=pb.AND_EXPR)
        assert needs_parens(parent, child) is False

    def test_or_inside_not_needs_parens(self):
        parent = pb.BoolExpr(boolop=pb.NOT_EXPR)
        child = pb.BoolExpr(boolop=pb.OR_EXPR)
        assert needs_parens(parent, child) is True

    def test_and_inside_not_needs_parens(self):
        parent = pb.BoolExpr(boolop=pb.NOT_EXPR)
        child = pb.BoolExpr(boolop=pb.AND_EXPR)
        assert needs_parens(parent, child) is True

    def test_addition_inside_multiplication_needs_parens(self):
        parent = _make_a_expr("*")
        child = _make_a_expr("+")
        assert needs_parens(parent, child) is True

    def test_multiplication_inside_addition_no_parens(self):
        parent = _make_a_expr("+")
        child = _make_a_expr("*")
        assert needs_parens(parent, child) is False

    def test_equal_comparison_is_nonassoc(self):
        parent = _make_a_expr("=")
        child = _make_a_expr("<")
        # Both are COMPARISON with nonassoc → needs parens
        assert needs_parens(parent, child) is True

    def test_atomic_child_never_needs_parens(self):
        parent = _make_a_expr("*")
        child = pb.ColumnRef()
        assert needs_parens(parent, child) is False

    def test_or_inside_comparison_needs_parens(self):
        parent = _make_a_expr("=")
        child = pb.BoolExpr(boolop=pb.OR_EXPR)
        assert needs_parens(parent, child) is True

    def test_add_inside_exponent_needs_parens(self):
        parent = _make_a_expr("^")
        child = _make_a_expr("+")
        assert needs_parens(parent, child) is True

    def test_same_left_assoc_no_parens(self):
        # a + b inside a + c — left-associative at same level, no parens needed
        parent = _make_a_expr("+")
        child = _make_a_expr("-")
        assert needs_parens(parent, child) is False


class TestPrecedenceClass:
    def test_repr(self):
        p = Precedence(level=5, assoc=Assoc.LEFT)
        assert "level=5" in repr(p)
        assert "Assoc.LEFT" in repr(p)

    def test_equality(self):
        a = Precedence(level=5, assoc=Assoc.LEFT)
        b = Precedence(level=5, assoc=Assoc.LEFT)
        assert a == b

    def test_inequality_level(self):
        a = Precedence(level=5, assoc=Assoc.LEFT)
        b = Precedence(level=6, assoc=Assoc.LEFT)
        assert a != b

    def test_inequality_assoc(self):
        a = Precedence(level=5, assoc=Assoc.LEFT)
        b = Precedence(level=5, assoc=Assoc.RIGHT)
        assert a != b

    def test_hash(self):
        a = Precedence(level=5, assoc=Assoc.LEFT)
        b = Precedence(level=5, assoc=Assoc.LEFT)
        assert hash(a) == hash(b)
        assert {a, b} == {a}

    def test_eq_with_non_precedence(self):
        p = Precedence(level=5, assoc=Assoc.LEFT)
        assert p != "not a precedence"


class TestFullLadder:
    """Verify the complete precedence ordering from loosest to tightest."""

    def test_complete_order(self):
        from postgast.precedence import (
            AT,
            COLLATE,
            DOT,
            ESCAPE,
            INTERSECT,
            PAREN,
            SUBSCRIPT,
            UNION,
        )

        levels = [
            UNION,
            INTERSECT,
            OR,
            AND,
            NOT,
            IS,
            COMPARISON,
            PATTERN,
            ESCAPE,
            OP,
            ADD_SUB,
            MUL_DIV,
            EXP,
            AT,
            COLLATE,
            UMINUS,
            SUBSCRIPT,
            PAREN,
            TYPECAST,
            DOT,
        ]
        for i in range(len(levels) - 1):
            assert levels[i] < levels[i + 1], f"{levels[i]} should be less than {levels[i + 1]}"
