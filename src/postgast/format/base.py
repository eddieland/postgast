"""Core formatter base class with emit helpers, node helpers, and shared clause visitors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import postgast.pg_query_pb2 as pb
from postgast.deparse import deparse
from postgast.format.constants import _TYPE_MAP  # pyright: ignore[reportPrivateUsage]
from postgast.format.utils import _pascal_to_snake, _quote_ident  # pyright: ignore[reportPrivateUsage]
from postgast.precedence import Side, needs_parens
from postgast.walk import Visitor, _unwrap_node  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from google.protobuf.message import Message


class _SqlFormatterBase(Visitor):
    """AST visitor base providing emit infrastructure and shared clause helpers."""

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._depth: int = 0
        self._at_line_start: bool = True
        self._in_clause_context: bool = False

    def reset(self) -> None:
        self._parts.clear()
        self._depth = 0
        self._at_line_start = True
        self._in_clause_context = False

    def get_output(self) -> str:
        return "".join(self._parts).rstrip()

    # ── Emit helpers ──────────────────────────────────────────────

    def _emit(self, text: str) -> None:
        if self._at_line_start and text and text != "\n":
            self._parts.append("  " * self._depth)
            self._at_line_start = False
        self._parts.append(text)

    def _newline(self) -> None:
        self._parts.append("\n")
        self._at_line_start = True

    def _indent(self) -> None:
        self._depth += 1

    def _dedent(self) -> None:
        self._depth -= 1

    def _emit_inline_list(self, items: Sequence[Any], *, visit: Callable[[Any], None] | None = None) -> None:
        """Emit items separated by ``', '``.  Uses *visit* (default ``_visit_node``) per item."""
        fn = visit or self._visit_node
        for i, item in enumerate(items):
            if i > 0:
                self._emit(", ")
            fn(item)

    def _emit_multiline_list(self, items: Sequence[Any], *, visit: Callable[[Any], None] | None = None) -> None:
        r"""Emit items separated by ``',\n'``.  Uses *visit* (default ``_visit_node``) per item."""
        fn = visit or self._visit_node
        for i, item in enumerate(items):
            if i > 0:
                self._emit(",")
                self._newline()
            fn(item)

    def _emit_string_or_visit(self, node: Any, *, quote: bool = False) -> None:
        """If *node* unwraps to a String, emit its sval (optionally quoted); else visit."""
        inner = _unwrap_node(node)
        if isinstance(inner, pb.String):
            self._emit(_quote_ident(inner.sval) if quote else inner.sval)
        else:
            self._visit_node(node)

    # ── Node helpers ──────────────────────────────────────────────

    def _fmt(self, node: Message) -> str:
        """Format a node and return its string representation."""
        saved_parts = self._parts
        saved_depth = self._depth
        saved_at_line_start = self._at_line_start
        self._parts = []
        self._depth = 0
        self._at_line_start = True
        self.visit(node)
        result = "".join(self._parts)
        self._parts = saved_parts
        self._depth = saved_depth
        self._at_line_start = saved_at_line_start
        return result

    def _visit_node(self, node: Message) -> None:
        """Visit a node in the current output context."""
        self.visit(node)

    def _visit_expr(self, parent: Message, child: Message, *, side: Side | None = None) -> None:
        """Visit a child expression, wrapping in parens when operator precedence requires it."""
        if needs_parens(parent, child, side=side):
            self._emit("(")
            self._visit_node(child)
            self._emit(")")
        else:
            self._visit_node(child)

    def _deparse_node(self, node: Message) -> str:
        """Deparse a single node via libpg_query as a fallback."""
        tree = pb.ParseResult()
        raw = tree.stmts.add()
        snake = _pascal_to_snake(type(node).DESCRIPTOR.name)
        getattr(raw.stmt, snake).CopyFrom(node)
        return deparse(tree)

    # ── Fallback ──────────────────────────────────────────────────

    def generic_visit(self, node: Message) -> None:  # pyright: ignore[reportImplicitOverride]  # type: ignore[override]
        try:
            text = self._deparse_node(node)
            self._emit(text)
        except Exception:
            super().generic_visit(node)

    # ── Shared type helpers ───────────────────────────────────────

    def _visit_type_name(self, tn: pb.TypeName) -> None:
        names = [cast("pb.String", _unwrap_node(n)).sval for n in tn.names]
        # Filter out 'pg_catalog' schema prefix for built-in types
        display_names = [n for n in names if n != "pg_catalog"]
        type_str = ".".join(display_names)
        type_str = _TYPE_MAP.get(type_str, type_str)
        self._emit(type_str)
        if tn.typmods:
            self._emit("(")
            self._emit_inline_list(tn.typmods)
            self._emit(")")
        if tn.array_bounds:
            for _ in tn.array_bounds:
                self._emit("[]")

    def visit_TypeName(self, node: pb.TypeName) -> None:
        self._visit_type_name(node)

    # ── Shared clause helpers ─────────────────────────────────────

    def _visit_res_target(self, node: Message) -> None:
        rt = cast("pb.ResTarget", node)
        self._visit_node(rt.val)
        if rt.name:
            self._emit(f" AS {rt.name}")

    def visit_ResTarget(self, node: pb.ResTarget) -> None:
        self._visit_res_target(node)

    def _visit_from_list(self, from_clause: Sequence[Any]) -> None:
        self._emit_multiline_list(from_clause, visit=lambda item: self._visit_node(_unwrap_node(item)))

    def _visit_where_expr(self, node: Message) -> None:
        """Visit a WHERE/HAVING expression, putting AND/OR on separate lines."""
        prev = self._in_clause_context
        self._in_clause_context = True
        self._visit_node(node)
        self._in_clause_context = prev

    def _emit_filter_clause(self, keyword: str, expr: Message) -> None:
        """Emit a WHERE/HAVING-style clause.  Inline for simple expressions, multiline for AND/OR."""
        inner = _unwrap_node(expr)
        is_compound = isinstance(inner, pb.BoolExpr) and inner.boolop in (pb.AND_EXPR, pb.OR_EXPR)
        self._newline()
        self._emit(keyword)
        if is_compound:
            self._newline()
            self._indent()
            self._visit_where_expr(expr)
            self._dedent()
        else:
            self._emit(" ")
            self._visit_node(expr)

    def _emit_where(self, where_clause: Message) -> None:
        """Emit a WHERE clause.  Inline for simple expressions, multiline for AND/OR."""
        self._emit_filter_clause("WHERE", where_clause)

    def _emit_from_clause(self, keyword: str, from_list: Sequence[Any]) -> None:
        """Emit a FROM/USING clause.  Inline for a single non-join item, multiline otherwise."""
        self._emit(keyword)
        if len(from_list) == 1 and not isinstance(_unwrap_node(from_list[0]), pb.JoinExpr):
            self._emit(" ")
            self._visit_node(_unwrap_node(from_list[0]))
        else:
            self._newline()
            self._indent()
            self._visit_from_list(from_list)
            self._dedent()

    def _emit_returning(self, returning_list: Sequence[Any]) -> None:
        """Emit a RETURNING clause.  Inline for a single target, multiline otherwise."""
        self._newline()
        self._emit("RETURNING")
        if len(returning_list) == 1:
            self._emit(" ")
            self._visit_res_target(_unwrap_node(returning_list[0]))
        else:
            self._newline()
            self._indent()
            self._emit_multiline_list(returning_list, visit=lambda t: self._visit_res_target(_unwrap_node(t)))
            self._dedent()

    def _emit_alias_colnames(self, colnames: Sequence[Any]) -> None:
        """Emit parenthesised column-name list for an alias (quoted identifiers)."""
        self._emit("(")
        self._emit_inline_list(colnames, visit=lambda cn: self._emit_string_or_visit(cn, quote=True))
        self._emit(")")

    def _emit_set_clause(self, target_list: Sequence[Any]) -> None:
        """Emit a SET clause.  Inline for a single assignment, multiline otherwise."""
        self._newline()
        self._emit("SET")
        if len(target_list) == 1:
            self._emit(" ")
            self._visit_set_assignment(target_list[0])
        else:
            self._newline()
            self._indent()
            self._emit_multiline_list(target_list, visit=self._visit_set_assignment)
            self._dedent()

    def _visit_set_assignment(self, item: Any) -> None:
        """Emit a single ``col = expr`` assignment inside a SET clause."""
        rt = _unwrap_node(item)
        if isinstance(rt, pb.ResTarget):
            self._emit(f"{rt.name} = ")
            self._visit_node(rt.val)
        else:
            self._visit_node(item)

    # ── ORDER BY ──────────────────────────────────────────────────

    def visit_SortBy(self, node: pb.SortBy) -> None:
        self._visit_node(node.node)
        if node.sortby_dir == pb.SORTBY_ASC:
            self._emit(" ASC")
        elif node.sortby_dir == pb.SORTBY_DESC:
            self._emit(" DESC")
        if node.sortby_nulls == pb.SORTBY_NULLS_FIRST:
            self._emit(" NULLS FIRST")
        elif node.sortby_nulls == pb.SORTBY_NULLS_LAST:
            self._emit(" NULLS LAST")

    # ── WITH / CTE ────────────────────────────────────────────────

    def _visit_with_clause(self, wc: pb.WithClause) -> None:
        self._emit("WITH")
        if wc.recursive:
            self._emit(" RECURSIVE")
        self._newline()
        self._indent()
        self._emit_multiline_list(wc.ctes, visit=lambda cte_node: self._visit_cte(_unwrap_node(cte_node)))
        self._dedent()
        self._newline()

    def _visit_cte(self, node: Message) -> None:
        cte = cast("pb.CommonTableExpr", node)
        self._emit(f"{cte.ctename} AS (")
        self._newline()
        self._indent()
        self._visit_node(cte.ctequery)
        self._newline()
        self._dedent()
        self._emit(")")

    def visit_CommonTableExpr(self, node: pb.CommonTableExpr) -> None:
        self._visit_cte(node)

    # ── Primitive value visitors ──────────────────────────────────

    def visit_String(self, node: pb.String) -> None:
        self._emit(node.sval)

    def visit_Integer(self, node: pb.Integer) -> None:
        self._emit(str(node.ival))

    def visit_Float(self, node: pb.Float) -> None:
        self._emit(node.fval)
