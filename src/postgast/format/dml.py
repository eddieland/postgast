"""DML statement (INSERT, UPDATE, DELETE) visitor methods for the SQL formatter."""

from __future__ import annotations

import postgast.pg_query_pb2 as pb
from postgast.format.base import _SqlFormatterBase  # pyright: ignore[reportPrivateUsage]
from postgast.walk import _unwrap_node  # pyright: ignore[reportPrivateUsage]


class _DmlMixin(_SqlFormatterBase):
    """Mixin providing DML statement visitor methods."""

    # ── INSERT ────────────────────────────────────────────────────

    def visit_InsertStmt(self, node: pb.InsertStmt) -> None:
        if node.HasField("with_clause"):
            self._visit_with_clause(node.with_clause)

        self._emit("INSERT INTO ")
        self._visit_node(node.relation)

        if node.cols:
            self._emit(" (")
            for i, col in enumerate(node.cols):
                if i > 0:
                    self._emit(", ")
                rt = _unwrap_node(col)
                if isinstance(rt, pb.ResTarget):
                    self._emit(rt.name)
                else:
                    self._visit_node(col)
            self._emit(")")

        if node.HasField("select_stmt"):
            self._newline()
            select = _unwrap_node(node.select_stmt)
            self._visit_node(select)

        if node.HasField("on_conflict_clause"):
            self._newline()
            self._visit_on_conflict(node.on_conflict_clause)

        if node.returning_list:
            self._emit_returning(node.returning_list)

    def _visit_on_conflict(self, oc: pb.OnConflictClause) -> None:
        self._emit("ON CONFLICT")
        if oc.HasField("infer"):
            if oc.infer.index_elems:
                self._emit(" (")
                self._emit_inline_list(oc.infer.index_elems)
                self._emit(")")
            elif oc.infer.conname:
                self._emit(f" ON CONSTRAINT {oc.infer.conname}")
        if oc.action == pb.ONCONFLICT_NOTHING:
            self._emit(" DO NOTHING")
        elif oc.action == pb.ONCONFLICT_UPDATE:
            self._emit(" DO UPDATE")
            self._emit_set_clause(oc.target_list)
            if oc.HasField("where_clause"):
                self._emit_where(oc.where_clause)

    # ── UPDATE ────────────────────────────────────────────────────

    def visit_UpdateStmt(self, node: pb.UpdateStmt) -> None:
        if node.HasField("with_clause"):
            self._visit_with_clause(node.with_clause)

        self._emit("UPDATE ")
        self._visit_node(node.relation)

        self._emit_set_clause(node.target_list)

        if node.from_clause:
            self._newline()
            self._emit_from_clause("FROM", node.from_clause)

        if node.HasField("where_clause"):
            self._emit_where(node.where_clause)

        if node.returning_list:
            self._emit_returning(node.returning_list)

    # ── DELETE ────────────────────────────────────────────────────

    def visit_DeleteStmt(self, node: pb.DeleteStmt) -> None:
        if node.HasField("with_clause"):
            self._visit_with_clause(node.with_clause)

        self._emit("DELETE FROM ")
        self._visit_node(node.relation)

        if node.using_clause:
            self._newline()
            self._emit_from_clause("USING", node.using_clause)

        if node.HasField("where_clause"):
            self._emit_where(node.where_clause)

        if node.returning_list:
            self._emit_returning(node.returning_list)
