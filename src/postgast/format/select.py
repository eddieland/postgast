"""SELECT statement and FROM clause visitor methods for the SQL formatter."""

from __future__ import annotations

from typing import cast

import postgast.pg_query_pb2 as pb
from postgast.format.base import _SqlFormatterBase  # pyright: ignore[reportPrivateUsage]
from postgast.format.constants import _GROUPING_SET_KW  # pyright: ignore[reportPrivateUsage]
from postgast.format.utils import _quote_ident  # pyright: ignore[reportPrivateUsage]
from postgast.walk import _unwrap_node  # pyright: ignore[reportPrivateUsage]


class _SelectMixin(_SqlFormatterBase):
    """Mixin providing SELECT statement and FROM clause visitor methods."""

    # ── SELECT statement ──────────────────────────────────────────

    def visit_SelectStmt(self, node: pb.SelectStmt) -> None:
        # Set operations (UNION / INTERSECT / EXCEPT)
        if node.op != pb.SETOP_NONE:
            self._visit_node(node.larg)
            self._newline()
            op_map = {
                pb.SETOP_UNION: "UNION",
                pb.SETOP_INTERSECT: "INTERSECT",
                pb.SETOP_EXCEPT: "EXCEPT",
            }
            op_str = op_map.get(node.op, "UNION")
            if node.all:
                op_str += " ALL"
            self._emit(op_str)
            self._newline()
            self._visit_node(node.rarg)
            return

        # VALUES list (standalone VALUES clause)
        if node.values_lists:
            self._emit("VALUES")
            self._newline()
            self._indent()
            for i, vals_node in enumerate(node.values_lists):
                if i > 0:
                    self._emit(",")
                    self._newline()
                vals = _unwrap_node(vals_node)
                self._emit("(")
                if isinstance(vals, pb.List):
                    for j, v in enumerate(vals.items):
                        if j > 0:
                            self._emit(", ")
                        self._visit_node(v)
                self._emit(")")
            self._dedent()
            return

        # WITH clause
        if node.HasField("with_clause"):
            self._visit_with_clause(node.with_clause)

        # SELECT [DISTINCT [ON (...)]]
        self._emit("SELECT")
        if node.distinct_clause:
            first = node.distinct_clause[0]
            if first.WhichOneof("node") is None:
                self._emit(" DISTINCT")
            else:
                self._emit(" DISTINCT ON (")
                self._emit_inline_list(node.distinct_clause)
                self._emit(")")

        # Target list — inline when a single, single-line target
        if len(node.target_list) == 1 and "\n" not in self._fmt(
            cast("pb.ResTarget", _unwrap_node(node.target_list[0]))
        ):
            self._emit(" ")
            self._visit_res_target(_unwrap_node(node.target_list[0]))
        else:
            self._newline()
            self._indent()
            self._emit_multiline_list(node.target_list, visit=lambda t: self._visit_res_target(_unwrap_node(t)))
            self._dedent()

        # FROM — inline when a single non-join item
        if node.from_clause:
            self._newline()
            self._emit_from_clause("FROM", node.from_clause)

        # WHERE
        if node.HasField("where_clause"):
            self._emit_where(node.where_clause)

        # GROUP BY — inline when a single item
        if node.group_clause:
            self._newline()
            self._emit("GROUP BY")
            if len(node.group_clause) == 1:
                self._emit(" ")
                self._visit_node(node.group_clause[0])
            else:
                self._newline()
                self._indent()
                self._emit_multiline_list(node.group_clause)
                self._dedent()

        # HAVING — inline for simple expressions, multiline for AND/OR
        if node.HasField("having_clause"):
            self._emit_filter_clause("HAVING", node.having_clause)

        # ORDER BY — inline when a single item
        if node.sort_clause:
            self._newline()
            self._emit("ORDER BY")
            if len(node.sort_clause) == 1:
                self._emit(" ")
                self._visit_node(node.sort_clause[0])
            else:
                self._newline()
                self._indent()
                self._emit_multiline_list(node.sort_clause)
                self._dedent()

        # LIMIT — always inline (single scalar value)
        if node.HasField("limit_count"):
            self._newline()
            self._emit("LIMIT ")
            self._visit_node(node.limit_count)

        # OFFSET — always inline (single scalar value)
        if node.HasField("limit_offset"):
            self._newline()
            self._emit("OFFSET ")
            self._visit_node(node.limit_offset)

        # Locking (FOR UPDATE/SHARE/NO KEY UPDATE/KEY SHARE)
        for lock in node.locking_clause:
            lc = cast("pb.LockingClause", _unwrap_node(lock))
            self._newline()
            strength_map = {
                pb.LCS_FORKEYSHARE: "FOR KEY SHARE",
                pb.LCS_FORSHARE: "FOR SHARE",
                pb.LCS_FORNOKEYUPDATE: "FOR NO KEY UPDATE",
                pb.LCS_FORUPDATE: "FOR UPDATE",
            }
            if lc.strength not in strength_map:
                msg = f"Unknown lock strength: {lc.strength}"
                raise ValueError(msg)
            self._emit(strength_map[lc.strength])
            if lc.locked_rels:
                self._emit(" OF ")
                self._emit_inline_list(lc.locked_rels)
            if lc.wait_policy == pb.LockWaitError:
                self._emit(" NOWAIT")
            elif lc.wait_policy == pb.LockWaitSkip:
                self._emit(" SKIP LOCKED")

    # ── FROM clause ───────────────────────────────────────────────

    def visit_RangeVar(self, node: pb.RangeVar) -> None:
        parts: list[str] = []
        if node.schemaname:
            parts.append(_quote_ident(node.schemaname))
        parts.append(_quote_ident(node.relname))
        self._emit(".".join(parts))
        if node.HasField("alias"):
            self._emit(f" {_quote_ident(node.alias.aliasname)}")

    def visit_RangeSubselect(self, node: pb.RangeSubselect) -> None:
        if node.lateral:
            self._emit("LATERAL ")
        self._emit("(")
        self._newline()
        self._indent()
        self._visit_node(node.subquery)
        self._newline()
        self._dedent()
        self._emit(")")
        if node.HasField("alias"):
            self._emit(f" AS {_quote_ident(node.alias.aliasname)}")
            if node.alias.colnames:
                self._emit_alias_colnames(node.alias.colnames)

    def visit_JoinExpr(self, node: pb.JoinExpr) -> None:
        self._visit_node(node.larg)
        self._newline()

        join_type_map = {
            pb.JOIN_INNER: "JOIN",
            pb.JOIN_LEFT: "LEFT JOIN",
            pb.JOIN_FULL: "FULL JOIN",
            pb.JOIN_RIGHT: "RIGHT JOIN",
        }
        join_kw = join_type_map.get(node.jointype, "JOIN")
        if node.is_natural:
            join_kw = f"NATURAL {join_kw}"
        elif node.jointype == pb.JOIN_INNER and not node.HasField("quals") and not node.using_clause:
            join_kw = "CROSS JOIN"

        self._emit(f"{join_kw} ")
        self._visit_node(node.rarg)

        if node.HasField("quals"):
            self._emit(" ON ")
            self._visit_node(node.quals)
        elif node.using_clause:
            self._emit(" USING (")
            self._emit_inline_list(node.using_clause, visit=self._emit_string_or_visit)
            self._emit(")")

    # ── RangeFunction ─────────────────────────────────────────────

    def visit_RangeFunction(self, node: pb.RangeFunction) -> None:
        if node.lateral:
            self._emit("LATERAL ")
        for func_item in node.functions:
            inner = _unwrap_node(func_item)
            if isinstance(inner, pb.List) and inner.items:
                self._visit_node(inner.items[0])
            else:
                self._visit_node(func_item)
        if node.HasField("alias"):
            self._emit(f" AS {_quote_ident(node.alias.aliasname)}")
            if node.alias.colnames:
                self._emit_alias_colnames(node.alias.colnames)

    # ── GroupingSet ───────────────────────────────────────────────

    def visit_GroupingSet(self, node: pb.GroupingSet) -> None:
        kind = node.kind
        if kind == pb.GROUPING_SET_EMPTY:
            self._emit("()")
        elif kind == pb.GROUPING_SET_SIMPLE:
            self._emit_inline_list(node.content)
        elif kind in _GROUPING_SET_KW:
            self._emit(_GROUPING_SET_KW[kind])
            self._emit_inline_list(node.content)
            self._emit(")")

    # ── RangeTableSample ──────────────────────────────────────────

    def visit_RangeTableSample(self, node: pb.RangeTableSample) -> None:
        self._visit_node(node.relation)
        self._emit(" TABLESAMPLE ")
        method_parts = [cast("pb.String", _unwrap_node(m)).sval for m in node.method]
        self._emit(".".join(method_parts))
        self._emit("(")
        self._emit_inline_list(node.args)
        self._emit(")")
        if node.HasField("repeatable"):
            self._emit(" REPEATABLE(")
            self._visit_node(node.repeatable)
            self._emit(")")
