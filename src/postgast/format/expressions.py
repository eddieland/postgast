"""Expression visitor methods for the SQL formatter."""

from __future__ import annotations

from typing import cast

import postgast.pg_query_pb2 as pb
from postgast.format.base import _SqlFormatterBase  # pyright: ignore[reportPrivateUsage]
from postgast.format.constants import (
    _FRAMEOPTION_BETWEEN,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_END_CURRENT_ROW,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_END_OFFSET_FOLLOWING,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_END_OFFSET_PRECEDING,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_END_UNBOUNDED_FOLLOWING,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_END_UNBOUNDED_PRECEDING,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_EXCLUDE_CURRENT_ROW,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_EXCLUDE_GROUP,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_EXCLUDE_TIES,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_GROUPS,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_NONDEFAULT,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_ROWS,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_START_CURRENT_ROW,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_START_OFFSET_FOLLOWING,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_START_OFFSET_PRECEDING,  # pyright: ignore[reportPrivateUsage]
    _FRAMEOPTION_START_UNBOUNDED_PRECEDING,  # pyright: ignore[reportPrivateUsage]
)
from postgast.format.utils import _quote_ident  # pyright: ignore[reportPrivateUsage]
from postgast.precedence import Side, needs_parens
from postgast.walk import _unwrap_node  # pyright: ignore[reportPrivateUsage]


class _ExpressionMixin(_SqlFormatterBase):
    """Mixin providing expression-formatting visitor methods."""

    def visit_A_Const(self, node: pb.A_Const) -> None:
        if node.isnull:
            self._emit("NULL")
        elif node.HasField("ival"):
            self._emit(str(node.ival.ival))
        elif node.HasField("fval"):
            self._emit(node.fval.fval)
        elif node.HasField("boolval"):
            self._emit("TRUE" if node.boolval.boolval else "FALSE")
        elif node.HasField("sval"):
            escaped = node.sval.sval.replace("'", "''")
            self._emit(f"'{escaped}'")
        elif node.HasField("bsval"):
            self._emit(node.bsval.bsval)

    def visit_ColumnRef(self, node: pb.ColumnRef) -> None:
        parts: list[str] = []
        for field_node in node.fields:
            inner = _unwrap_node(field_node)
            if isinstance(inner, pb.String):
                parts.append(_quote_ident(inner.sval))
            elif isinstance(inner, pb.A_Star):
                parts.append("*")
        self._emit(".".join(parts))

    def visit_A_Expr(self, node: pb.A_Expr) -> None:
        op_name = ""
        if node.name:
            op_name = cast("pb.String", _unwrap_node(node.name[0])).sval

        kind = node.kind

        if kind == pb.AEXPR_OP:
            if node.HasField("lexpr"):
                self._visit_expr(node, node.lexpr, side=Side.LEFT)
                self._emit(f" {op_name} ")
                self._visit_expr(node, node.rexpr, side=Side.RIGHT)
            else:
                # Unary prefix operator
                self._emit(f"{op_name} ")
                self._visit_expr(node, node.rexpr)

        elif kind == pb.AEXPR_IN:
            self._visit_expr(node, node.lexpr, side=Side.LEFT)
            # op_name is "=" for IN, "<>" for NOT IN in the AST
            in_kw = "NOT IN" if op_name == "<>" else "IN"
            self._emit(f" {in_kw} (")
            inner = _unwrap_node(node.rexpr)
            if isinstance(inner, pb.List):
                for i, item in enumerate(inner.items):
                    if i > 0:
                        self._emit(", ")
                    self._visit_node(item)
            else:
                self._visit_node(node.rexpr)
            self._emit(")")

        elif kind in (pb.AEXPR_LIKE, pb.AEXPR_ILIKE):
            self._visit_expr(node, node.lexpr, side=Side.LEFT)
            kw = "LIKE" if kind == pb.AEXPR_LIKE else "ILIKE"
            self._emit(f" {kw} ")
            self._visit_expr(node, node.rexpr, side=Side.RIGHT)

        elif kind in (pb.AEXPR_BETWEEN, pb.AEXPR_NOT_BETWEEN):
            self._visit_expr(node, node.lexpr, side=Side.LEFT)
            kw = "BETWEEN" if kind == pb.AEXPR_BETWEEN else "NOT BETWEEN"
            self._emit(f" {kw} ")
            args = _unwrap_node(node.rexpr)
            if isinstance(args, pb.List) and len(args.items) == 2:
                self._visit_node(args.items[0])
                self._emit(" AND ")
                self._visit_node(args.items[1])
            else:
                self._visit_node(node.rexpr)

        elif kind == pb.AEXPR_DISTINCT:
            self._visit_node(node.lexpr)
            self._emit(" IS DISTINCT FROM ")
            self._visit_node(node.rexpr)

        elif kind == pb.AEXPR_NOT_DISTINCT:
            self._visit_node(node.lexpr)
            self._emit(" IS NOT DISTINCT FROM ")
            self._visit_node(node.rexpr)

        elif kind == pb.AEXPR_NULLIF:
            self._emit("NULLIF(")
            self._visit_node(node.lexpr)
            self._emit(", ")
            self._visit_node(node.rexpr)
            self._emit(")")

        elif kind in (pb.AEXPR_OP_ANY, pb.AEXPR_OP_ALL):
            self._visit_expr(node, node.lexpr, side=Side.LEFT)
            quantifier = "ANY" if kind == pb.AEXPR_OP_ANY else "ALL"
            self._emit(f" {op_name} {quantifier}(")
            self._visit_node(node.rexpr)
            self._emit(")")

        elif kind in (pb.AEXPR_SIMILAR, pb.AEXPR_BETWEEN_SYM, pb.AEXPR_NOT_BETWEEN_SYM):
            # Fallback for rare expression kinds
            text = self._deparse_node(node)
            self._emit(text)

        else:
            text = self._deparse_node(node)
            self._emit(text)

    def visit_BoolExpr(self, node: pb.BoolExpr) -> None:
        if node.boolop == pb.NOT_EXPR:
            self._emit("NOT ")
            child = node.args[0]
            if needs_parens(node, child):
                self._emit("(")
                prev = self._in_clause_context
                self._in_clause_context = False
                self._visit_node(child)
                self._in_clause_context = prev
                self._emit(")")
            else:
                self._visit_node(child)
            return

        op = "AND" if node.boolop == pb.AND_EXPR else "OR"
        if self._in_clause_context:
            for i, arg in enumerate(node.args):
                if i > 0:
                    self._newline()
                    self._emit(f"{op} ")
                if needs_parens(node, arg):
                    self._emit("(")
                    prev = self._in_clause_context
                    self._in_clause_context = False
                    self._visit_node(arg)
                    self._in_clause_context = prev
                    self._emit(")")
                else:
                    self._visit_node(arg)
        else:
            for i, arg in enumerate(node.args):
                if i > 0:
                    self._emit(f" {op} ")
                if needs_parens(node, arg):
                    self._emit("(")
                    self._visit_node(arg)
                    self._emit(")")
                else:
                    self._visit_node(arg)

    def visit_FuncCall(self, node: pb.FuncCall) -> None:
        name_parts = [cast("pb.String", _unwrap_node(n)).sval for n in node.funcname]
        display_parts = name_parts[1:] if len(name_parts) > 1 and name_parts[0] == "pg_catalog" else name_parts
        self._emit(".".join(display_parts))
        self._emit("(")
        if node.agg_star:
            self._emit("*")
        else:
            if node.agg_distinct:
                self._emit("DISTINCT ")
            self._emit_inline_list(node.args)
            if node.agg_order:
                self._emit(" ORDER BY ")
                self._emit_inline_list(node.agg_order)
        self._emit(")")
        if node.HasField("agg_filter"):
            self._emit(" FILTER (WHERE ")
            self._visit_node(node.agg_filter)
            self._emit(")")
        if node.HasField("over"):
            self._emit(" OVER ")
            self._visit_window_def(node.over)

    def _visit_window_def(self, wdef: pb.WindowDef) -> None:
        if wdef.name:
            self._emit(wdef.name)
            return
        if wdef.refname:
            self._emit(f"({wdef.refname})")
            return
        self._emit("(")
        parts_emitted = False
        if wdef.partition_clause:
            self._emit("PARTITION BY ")
            self._emit_inline_list(wdef.partition_clause)
            parts_emitted = True
        if wdef.order_clause:
            if parts_emitted:
                self._emit(" ")
            self._emit("ORDER BY ")
            self._emit_inline_list(wdef.order_clause)
            parts_emitted = True
        if wdef.frame_options & _FRAMEOPTION_NONDEFAULT:
            if parts_emitted:
                self._emit(" ")
            self._visit_window_frame(wdef)
        self._emit(")")

    def _visit_window_frame(self, wdef: pb.WindowDef) -> None:
        fopts = wdef.frame_options
        # Mode
        if fopts & _FRAMEOPTION_ROWS:
            self._emit("ROWS")
        elif fopts & _FRAMEOPTION_GROUPS:
            self._emit("GROUPS")
        else:
            self._emit("RANGE")

        has_between = bool(fopts & _FRAMEOPTION_BETWEEN)
        if has_between:
            self._emit(" BETWEEN ")
        else:
            self._emit(" ")

        # Start bound
        if fopts & _FRAMEOPTION_START_UNBOUNDED_PRECEDING:
            self._emit("UNBOUNDED PRECEDING")
        elif fopts & _FRAMEOPTION_START_CURRENT_ROW:
            self._emit("CURRENT ROW")
        elif fopts & _FRAMEOPTION_START_OFFSET_PRECEDING:
            self._visit_node(wdef.start_offset)
            self._emit(" PRECEDING")
        elif fopts & _FRAMEOPTION_START_OFFSET_FOLLOWING:
            self._visit_node(wdef.start_offset)
            self._emit(" FOLLOWING")

        if has_between:
            self._emit(" AND ")
            # End bound
            if fopts & _FRAMEOPTION_END_UNBOUNDED_FOLLOWING:
                self._emit("UNBOUNDED FOLLOWING")
            elif fopts & _FRAMEOPTION_END_CURRENT_ROW:
                self._emit("CURRENT ROW")
            elif fopts & _FRAMEOPTION_END_OFFSET_PRECEDING:
                self._visit_node(wdef.end_offset)
                self._emit(" PRECEDING")
            elif fopts & _FRAMEOPTION_END_OFFSET_FOLLOWING:
                self._visit_node(wdef.end_offset)
                self._emit(" FOLLOWING")
            elif fopts & _FRAMEOPTION_END_UNBOUNDED_PRECEDING:
                self._emit("UNBOUNDED PRECEDING")

        # EXCLUDE options
        if fopts & _FRAMEOPTION_EXCLUDE_CURRENT_ROW:
            self._emit(" EXCLUDE CURRENT ROW")
        elif fopts & _FRAMEOPTION_EXCLUDE_GROUP:
            self._emit(" EXCLUDE GROUP")
        elif fopts & _FRAMEOPTION_EXCLUDE_TIES:
            self._emit(" EXCLUDE TIES")

    def visit_TypeCast(self, node: pb.TypeCast) -> None:
        self._visit_expr(node, node.arg, side=Side.LEFT)
        self._emit("::")
        self._visit_type_name(node.type_name)

    def visit_CaseExpr(self, node: pb.CaseExpr) -> None:
        self._emit("CASE")
        if node.HasField("arg"):
            self._emit(" ")
            self._visit_node(node.arg)
        self._newline()
        self._indent()
        for when_node in node.args:
            self._visit_node(when_node)
        if node.HasField("defresult"):
            self._emit("ELSE ")
            self._visit_node(node.defresult)
            self._newline()
        self._dedent()
        self._emit("END")

    def visit_CaseWhen(self, node: pb.CaseWhen) -> None:
        self._emit("WHEN ")
        self._visit_node(node.expr)
        self._emit(" THEN ")
        self._visit_node(node.result)
        self._newline()

    def visit_SubLink(self, node: pb.SubLink) -> None:
        stype = node.sub_link_type
        if stype == pb.EXISTS_SUBLINK:
            self._emit("EXISTS (")
            self._newline()
            self._indent()
            self._visit_node(node.subselect)
            self._newline()
            self._dedent()
            self._emit(")")
        elif stype in (pb.ANY_SUBLINK, pb.ALL_SUBLINK):
            quantifier = "ANY" if stype == pb.ANY_SUBLINK else "ALL"
            self._visit_node(node.testexpr)
            op = cast("pb.String", _unwrap_node(node.oper_name[0])).sval if node.oper_name else "="
            self._emit(f" {op} {quantifier}(")
            self._newline()
            self._indent()
            self._visit_node(node.subselect)
            self._newline()
            self._dedent()
            self._emit(")")
        elif stype == pb.EXPR_SUBLINK:
            self._emit("(")
            self._newline()
            self._indent()
            self._visit_node(node.subselect)
            self._newline()
            self._dedent()
            self._emit(")")
        else:
            # ROWCOMPARE, MULTIEXPR, ARRAY, CTE — fallback
            text = self._deparse_node(node)
            self._emit(text)

    def visit_NullTest(self, node: pb.NullTest) -> None:
        self._visit_expr(node, node.arg, side=Side.LEFT)
        if node.nulltesttype == pb.IS_NULL:
            self._emit(" IS NULL")
        else:
            self._emit(" IS NOT NULL")

    def visit_BooleanTest(self, node: pb.BooleanTest) -> None:
        self._visit_expr(node, node.arg, side=Side.LEFT)
        _map = {
            pb.IS_TRUE: " IS TRUE",
            pb.IS_NOT_TRUE: " IS NOT TRUE",
            pb.IS_FALSE: " IS FALSE",
            pb.IS_NOT_FALSE: " IS NOT FALSE",
            pb.IS_UNKNOWN: " IS UNKNOWN",
            pb.IS_NOT_UNKNOWN: " IS NOT UNKNOWN",
        }
        self._emit(_map.get(node.booltesttype, ""))

    def visit_CoalesceExpr(self, node: pb.CoalesceExpr) -> None:
        self._emit("COALESCE(")
        self._emit_inline_list(node.args)
        self._emit(")")

    def visit_MinMaxExpr(self, node: pb.MinMaxExpr) -> None:
        func = "GREATEST" if node.op == pb.IS_GREATEST else "LEAST"
        self._emit(f"{func}(")
        self._emit_inline_list(node.args)
        self._emit(")")

    def visit_ParamRef(self, node: pb.ParamRef) -> None:
        if node.number > 0:
            self._emit(f"${node.number}")
        else:
            self._emit("$0")

    def visit_A_Star(self, _node: pb.A_Star) -> None:
        self._emit("*")

    def visit_A_Indirection(self, node: pb.A_Indirection) -> None:
        self._visit_node(node.arg)
        for ind in node.indirection:
            inner = _unwrap_node(ind)
            if isinstance(inner, pb.String):
                self._emit(f".{inner.sval}")
            elif isinstance(inner, pb.A_Indices):
                self._emit("[")
                if inner.HasField("lidx"):
                    self._visit_node(inner.lidx)
                    self._emit(":")
                if inner.HasField("uidx"):
                    self._visit_node(inner.uidx)
                self._emit("]")
            else:
                self._emit(".")
                self._visit_node(ind)

    def visit_A_ArrayExpr(self, node: pb.A_ArrayExpr) -> None:
        self._emit("ARRAY[")
        self._emit_inline_list(node.elements)
        self._emit("]")

    def visit_RowExpr(self, node: pb.RowExpr) -> None:
        if node.row_format == pb.COERCE_EXPLICIT_CALL:
            self._emit("ROW(")
        else:
            self._emit("(")
        self._emit_inline_list(node.args)
        self._emit(")")
