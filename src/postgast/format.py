"""SQL pretty-printer that walks the protobuf AST and emits formatted SQL."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import postgast.pg_query_pb2 as pb
from postgast.deparse import deparse
from postgast.parse import parse
from postgast.walk import Visitor, _unwrap_node  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from collections.abc import Sequence

    from google.protobuf.message import Message

    from postgast.pg_query_pb2 import ParseResult


def format_sql(sql: str | ParseResult) -> str:
    """Format a SQL string or ParseResult into a canonical, readable layout.

    Args:
        sql: A SQL string or an already-parsed ``ParseResult``.

    Returns:
        A pretty-printed SQL string with uppercase keywords, clause-per-line
        layout, and indented bodies.  Each statement ends with a semicolon.

    Raises:
        PgQueryError: If *sql* is a string that cannot be parsed.
    """
    tree: ParseResult = parse(sql) if isinstance(sql, str) else sql
    formatter = _SqlFormatter()
    parts: list[str] = []
    for raw_stmt in tree.stmts:
        stmt = _unwrap_node(raw_stmt.stmt)
        formatter.reset()
        formatter.visit(stmt)
        parts.append(formatter.get_output())
    return ";\n\n".join(parts) + ";" if parts else ""


class _SqlFormatter(Visitor):
    """AST visitor that emits formatted SQL."""

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._depth: int = 0
        self._at_line_start: bool = True

    def reset(self) -> None:
        self._parts.clear()
        self._depth = 0
        self._at_line_start = True

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

    def _deparse_node(self, node: Message) -> str:
        """Deparse a single node via libpg_query as a fallback."""
        tree = pb.ParseResult()
        raw = tree.stmts.add()
        target_field = type(node).DESCRIPTOR.name
        # Convert PascalCase to snake_case for the Node oneof field name
        snake = ""
        for i, ch in enumerate(target_field):
            if ch.isupper() and i > 0:
                snake += "_"
            snake += ch.lower()
        getattr(raw.stmt, snake).CopyFrom(node)
        return deparse(tree)

    # ── Fallback ──────────────────────────────────────────────────

    def generic_visit(self, node: Message) -> None:  # pyright: ignore[reportImplicitOverride]  # type: ignore[override]
        try:
            text = self._deparse_node(node)
            self._emit(text)
        except Exception:
            super().generic_visit(node)

    # ── Expression visitors ───────────────────────────────────────

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
                parts.append(inner.sval)
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
                self._visit_node(node.lexpr)
                self._emit(f" {op_name} ")
                self._visit_node(node.rexpr)
            else:
                # Unary prefix operator
                self._emit(f"{op_name} ")
                self._visit_node(node.rexpr)

        elif kind == pb.AEXPR_IN:
            self._visit_node(node.lexpr)
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
            self._visit_node(node.lexpr)
            kw = "LIKE" if kind == pb.AEXPR_LIKE else "ILIKE"
            self._emit(f" {kw} ")
            self._visit_node(node.rexpr)

        elif kind in (pb.AEXPR_BETWEEN, pb.AEXPR_NOT_BETWEEN):
            self._visit_node(node.lexpr)
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
            self._visit_node(node.lexpr)
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
            self._visit_node(node.args[0])
            return

        op = "AND" if node.boolop == pb.AND_EXPR else "OR"
        for i, arg in enumerate(node.args):
            if i > 0:
                self._newline()
                self._emit(f"{op} ")
            self._visit_node(arg)

    def visit_FuncCall(self, node: pb.FuncCall) -> None:
        name_parts = [cast("pb.String", _unwrap_node(n)).sval for n in node.funcname]
        self._emit(".".join(name_parts))
        self._emit("(")
        if node.agg_star:
            self._emit("*")
        else:
            if node.agg_distinct:
                self._emit("DISTINCT ")
            for i, arg in enumerate(node.args):
                if i > 0:
                    self._emit(", ")
                self._visit_node(arg)
            if node.agg_order:
                self._emit(" ORDER BY ")
                for i, sort_item in enumerate(node.agg_order):
                    if i > 0:
                        self._emit(", ")
                    self._visit_node(sort_item)
        if node.HasField("agg_filter"):
            self._emit(") FILTER (WHERE ")
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
            for i, item in enumerate(wdef.partition_clause):
                if i > 0:
                    self._emit(", ")
                self._visit_node(item)
            parts_emitted = True
        if wdef.order_clause:
            if parts_emitted:
                self._emit(" ")
            self._emit("ORDER BY ")
            for i, item in enumerate(wdef.order_clause):
                if i > 0:
                    self._emit(", ")
                self._visit_node(item)
        self._emit(")")

    def visit_TypeCast(self, node: pb.TypeCast) -> None:
        self._visit_node(node.arg)
        self._emit("::")
        self._visit_type_name(node.type_name)

    def _visit_type_name(self, tn: pb.TypeName) -> None:
        names = [cast("pb.String", _unwrap_node(n)).sval for n in tn.names]
        # Filter out 'pg_catalog' schema prefix for built-in types
        display_names = [n for n in names if n != "pg_catalog"]
        type_str = ".".join(display_names)
        # Map internal type names to SQL type names
        _type_map: dict[str, str] = {
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
        type_str = _type_map.get(type_str, type_str)
        self._emit(type_str)
        if tn.typmods:
            self._emit("(")
            for i, mod in enumerate(tn.typmods):
                if i > 0:
                    self._emit(", ")
                self._visit_node(mod)
            self._emit(")")
        if tn.array_bounds:
            for _ in tn.array_bounds:
                self._emit("[]")

    def visit_TypeName(self, node: pb.TypeName) -> None:
        self._visit_type_name(node)

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
        elif stype == pb.ANY_SUBLINK:
            self._visit_node(node.testexpr)
            op = cast("pb.String", _unwrap_node(node.oper_name[0])).sval if node.oper_name else "="
            self._emit(f" {op} ANY(")
            self._newline()
            self._indent()
            self._visit_node(node.subselect)
            self._newline()
            self._dedent()
            self._emit(")")
        elif stype == pb.ALL_SUBLINK:
            self._visit_node(node.testexpr)
            op = cast("pb.String", _unwrap_node(node.oper_name[0])).sval if node.oper_name else "="
            self._emit(f" {op} ALL(")
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
        self._visit_node(node.arg)
        if node.nulltesttype == pb.IS_NULL:
            self._emit(" IS NULL")
        else:
            self._emit(" IS NOT NULL")

    def visit_BooleanTest(self, node: pb.BooleanTest) -> None:
        self._visit_node(node.arg)
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
        for i, arg in enumerate(node.args):
            if i > 0:
                self._emit(", ")
            self._visit_node(arg)
        self._emit(")")

    def visit_MinMaxExpr(self, node: pb.MinMaxExpr) -> None:
        func = "GREATEST" if node.op == pb.IS_GREATEST else "LEAST"
        self._emit(f"{func}(")
        for i, arg in enumerate(node.args):
            if i > 0:
                self._emit(", ")
            self._visit_node(arg)
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
        for i, elem in enumerate(node.elements):
            if i > 0:
                self._emit(", ")
            self._visit_node(elem)
        self._emit("]")

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

        # SELECT [DISTINCT]
        self._emit("SELECT")
        if node.distinct_clause:
            self._emit(" DISTINCT")
        self._newline()

        # Target list
        self._indent()
        for i, target in enumerate(node.target_list):
            if i > 0:
                self._emit(",")
                self._newline()
            self._visit_res_target(_unwrap_node(target))
        self._dedent()

        # FROM
        if node.from_clause:
            self._newline()
            self._emit("FROM")
            self._newline()
            self._indent()
            self._visit_from_list(node.from_clause)
            self._dedent()

        # WHERE
        if node.HasField("where_clause"):
            self._newline()
            self._emit("WHERE")
            self._newline()
            self._indent()
            self._visit_where_expr(node.where_clause)
            self._dedent()

        # GROUP BY
        if node.group_clause:
            self._newline()
            self._emit("GROUP BY")
            self._newline()
            self._indent()
            for i, item in enumerate(node.group_clause):
                if i > 0:
                    self._emit(",")
                    self._newline()
                self._visit_node(item)
            self._dedent()

        # HAVING
        if node.HasField("having_clause"):
            self._newline()
            self._emit("HAVING")
            self._newline()
            self._indent()
            self._visit_where_expr(node.having_clause)
            self._dedent()

        # ORDER BY
        if node.sort_clause:
            self._newline()
            self._emit("ORDER BY")
            self._newline()
            self._indent()
            for i, item in enumerate(node.sort_clause):
                if i > 0:
                    self._emit(",")
                    self._newline()
                self._visit_node(item)
            self._dedent()

        # LIMIT
        if node.HasField("limit_count"):
            self._newline()
            self._emit("LIMIT")
            self._newline()
            self._indent()
            self._visit_node(node.limit_count)
            self._dedent()

        # OFFSET
        if node.HasField("limit_offset"):
            self._newline()
            self._emit("OFFSET")
            self._newline()
            self._indent()
            self._visit_node(node.limit_offset)
            self._dedent()

        # Locking (FOR UPDATE/SHARE)
        for lock in node.locking_clause:
            inner = _unwrap_node(lock)
            text = self._deparse_node(inner)
            self._newline()
            self._emit(text)

    def _visit_res_target(self, node: Message) -> None:
        rt = cast("pb.ResTarget", node)
        self._visit_node(rt.val)
        if rt.name:
            self._emit(f" AS {rt.name}")

    def visit_ResTarget(self, node: pb.ResTarget) -> None:
        self._visit_res_target(node)

    # ── FROM clause helpers ───────────────────────────────────────

    def _visit_from_list(self, from_clause: Sequence[Any]) -> None:
        for i, item in enumerate(from_clause):
            if i > 0:
                self._emit(",")
                self._newline()
            inner = _unwrap_node(item)
            self._visit_node(inner)

    def visit_RangeVar(self, node: pb.RangeVar) -> None:
        parts: list[str] = []
        if node.schemaname:
            parts.append(node.schemaname)
        parts.append(node.relname)
        self._emit(".".join(parts))
        if node.HasField("alias"):
            self._emit(f" {node.alias.aliasname}")

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
            self._emit(f" AS {node.alias.aliasname}")

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

        # CROSS JOIN has no quals
        if not node.HasField("quals") and not node.using_clause:
            join_kw = "CROSS JOIN"

        self._emit(f"{join_kw} ")
        self._visit_node(node.rarg)

        if node.HasField("quals"):
            self._emit(" ON ")
            self._visit_node(node.quals)
        elif node.using_clause:
            self._emit(" USING (")
            for i, col in enumerate(node.using_clause):
                if i > 0:
                    self._emit(", ")
                inner = _unwrap_node(col)
                if isinstance(inner, pb.String):
                    self._emit(inner.sval)
                else:
                    self._visit_node(col)
            self._emit(")")

    # ── WHERE expression helper ───────────────────────────────────

    def _visit_where_expr(self, node: Message) -> None:
        """Visit a WHERE/HAVING expression, putting AND/OR on separate lines."""
        self._visit_node(node)

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
        for i, cte_node in enumerate(wc.ctes):
            if i > 0:
                self._emit(",")
                self._newline()
            cte = _unwrap_node(cte_node)
            self._visit_cte(cte)
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
            self._newline()
            self._emit("RETURNING")
            self._newline()
            self._indent()
            for i, item in enumerate(node.returning_list):
                if i > 0:
                    self._emit(",")
                    self._newline()
                self._visit_res_target(_unwrap_node(item))
            self._dedent()

    def _visit_on_conflict(self, oc: pb.OnConflictClause) -> None:
        self._emit("ON CONFLICT")
        if oc.HasField("infer"):
            if oc.infer.index_elems:
                self._emit(" (")
                for i, elem in enumerate(oc.infer.index_elems):
                    if i > 0:
                        self._emit(", ")
                    self._visit_node(elem)
                self._emit(")")
            elif oc.infer.conname:
                self._emit(f" ON CONSTRAINT {oc.infer.conname}")
        if oc.action == pb.ONCONFLICT_NOTHING:
            self._emit(" DO NOTHING")
        elif oc.action == pb.ONCONFLICT_UPDATE:
            self._emit(" DO UPDATE")
            self._newline()
            self._emit("SET")
            self._newline()
            self._indent()
            for i, item in enumerate(oc.target_list):
                if i > 0:
                    self._emit(",")
                    self._newline()
                rt = _unwrap_node(item)
                if isinstance(rt, pb.ResTarget):
                    self._emit(f"{rt.name} = ")
                    self._visit_node(rt.val)
                else:
                    self._visit_node(item)
            self._dedent()
            if oc.HasField("where_clause"):
                self._newline()
                self._emit("WHERE")
                self._newline()
                self._indent()
                self._visit_where_expr(oc.where_clause)
                self._dedent()

    # ── UPDATE ────────────────────────────────────────────────────

    def visit_UpdateStmt(self, node: pb.UpdateStmt) -> None:
        if node.HasField("with_clause"):
            self._visit_with_clause(node.with_clause)

        self._emit("UPDATE ")
        self._visit_node(node.relation)

        self._newline()
        self._emit("SET")
        self._newline()
        self._indent()
        for i, item in enumerate(node.target_list):
            if i > 0:
                self._emit(",")
                self._newline()
            rt = _unwrap_node(item)
            if isinstance(rt, pb.ResTarget):
                self._emit(f"{rt.name} = ")
                self._visit_node(rt.val)
            else:
                self._visit_node(item)
        self._dedent()

        if node.from_clause:
            self._newline()
            self._emit("FROM")
            self._newline()
            self._indent()
            self._visit_from_list(node.from_clause)
            self._dedent()

        if node.HasField("where_clause"):
            self._newline()
            self._emit("WHERE")
            self._newline()
            self._indent()
            self._visit_where_expr(node.where_clause)
            self._dedent()

        if node.returning_list:
            self._newline()
            self._emit("RETURNING")
            self._newline()
            self._indent()
            for i, item in enumerate(node.returning_list):
                if i > 0:
                    self._emit(",")
                    self._newline()
                self._visit_res_target(_unwrap_node(item))
            self._dedent()

    # ── DELETE ────────────────────────────────────────────────────

    def visit_DeleteStmt(self, node: pb.DeleteStmt) -> None:
        if node.HasField("with_clause"):
            self._visit_with_clause(node.with_clause)

        self._emit("DELETE FROM ")
        self._visit_node(node.relation)

        if node.using_clause:
            self._newline()
            self._emit("USING")
            self._newline()
            self._indent()
            self._visit_from_list(node.using_clause)
            self._dedent()

        if node.HasField("where_clause"):
            self._newline()
            self._emit("WHERE")
            self._newline()
            self._indent()
            self._visit_where_expr(node.where_clause)
            self._dedent()

        if node.returning_list:
            self._newline()
            self._emit("RETURNING")
            self._newline()
            self._indent()
            for i, item in enumerate(node.returning_list):
                if i > 0:
                    self._emit(",")
                    self._newline()
                self._visit_res_target(_unwrap_node(item))
            self._dedent()

    # ── CREATE TABLE ──────────────────────────────────────────────

    def visit_CreateStmt(self, node: pb.CreateStmt) -> None:
        self._emit("CREATE TABLE ")
        if node.if_not_exists:
            self._emit("IF NOT EXISTS ")
        self._visit_node(node.relation)
        self._emit(" (")
        self._newline()
        self._indent()
        all_elts = list(node.table_elts) + list(node.constraints)
        for i, elt in enumerate(all_elts):
            if i > 0:
                self._emit(",")
                self._newline()
            inner = _unwrap_node(elt)
            if isinstance(inner, pb.ColumnDef):
                self._visit_column_def(inner)
            elif isinstance(inner, pb.Constraint):
                self._visit_constraint(inner)
            else:
                self._visit_node(elt)
        self._newline()
        self._dedent()
        self._emit(")")
        if node.inh_relations:
            self._emit(" INHERITS (")
            for i, rel in enumerate(node.inh_relations):
                if i > 0:
                    self._emit(", ")
                self._visit_node(rel)
            self._emit(")")

    def _visit_column_def(self, node: pb.ColumnDef) -> None:
        self._emit(f"{node.colname} ")
        self._visit_type_name(node.type_name)
        for cons in node.constraints:
            inner = _unwrap_node(cons)
            if isinstance(inner, pb.Constraint):
                self._emit(" ")
                self._visit_inline_constraint(inner)

    def _visit_inline_constraint(self, node: pb.Constraint) -> None:
        contype = node.contype
        if contype == pb.CONSTR_NOTNULL:
            self._emit("NOT NULL")
        elif contype == pb.CONSTR_NULL:
            self._emit("NULL")
        elif contype == pb.CONSTR_DEFAULT:
            self._emit("DEFAULT ")
            if node.HasField("raw_expr"):
                self._visit_node(node.raw_expr)
        elif contype == pb.CONSTR_CHECK:
            self._emit("CHECK (")
            if node.HasField("raw_expr"):
                self._visit_node(node.raw_expr)
            self._emit(")")
        elif contype == pb.CONSTR_PRIMARY:
            self._emit("PRIMARY KEY")
        elif contype == pb.CONSTR_UNIQUE:
            self._emit("UNIQUE")
        elif contype == pb.CONSTR_FOREIGN:
            self._emit("REFERENCES ")
            if node.HasField("pktable"):
                self._visit_node(node.pktable)
            if node.pk_attrs:
                self._emit(" (")
                for i, attr in enumerate(node.pk_attrs):
                    if i > 0:
                        self._emit(", ")
                    inner = _unwrap_node(attr)
                    if isinstance(inner, pb.String):
                        self._emit(inner.sval)
                    else:
                        self._visit_node(attr)
                self._emit(")")
        elif contype == pb.CONSTR_IDENTITY:
            self._emit("GENERATED ALWAYS AS IDENTITY")
        else:
            # Fallback for other constraint types
            pass

    def _visit_constraint(self, node: pb.Constraint) -> None:
        """Visit a table-level constraint."""
        if node.conname:
            self._emit(f"CONSTRAINT {node.conname} ")
        contype = node.contype
        if contype == pb.CONSTR_PRIMARY:
            self._emit("PRIMARY KEY (")
            for i, key in enumerate(node.keys):
                if i > 0:
                    self._emit(", ")
                inner = _unwrap_node(key)
                if isinstance(inner, pb.String):
                    self._emit(inner.sval)
                else:
                    self._visit_node(key)
            self._emit(")")
        elif contype == pb.CONSTR_UNIQUE:
            self._emit("UNIQUE (")
            for i, key in enumerate(node.keys):
                if i > 0:
                    self._emit(", ")
                inner = _unwrap_node(key)
                if isinstance(inner, pb.String):
                    self._emit(inner.sval)
                else:
                    self._visit_node(key)
            self._emit(")")
        elif contype == pb.CONSTR_CHECK:
            self._emit("CHECK (")
            if node.HasField("raw_expr"):
                self._visit_node(node.raw_expr)
            self._emit(")")
        elif contype == pb.CONSTR_FOREIGN:
            self._emit("FOREIGN KEY (")
            for i, attr in enumerate(node.fk_attrs):
                if i > 0:
                    self._emit(", ")
                inner = _unwrap_node(attr)
                if isinstance(inner, pb.String):
                    self._emit(inner.sval)
                else:
                    self._visit_node(attr)
            self._emit(") REFERENCES ")
            if node.HasField("pktable"):
                self._visit_node(node.pktable)
            if node.pk_attrs:
                self._emit(" (")
                for i, attr in enumerate(node.pk_attrs):
                    if i > 0:
                        self._emit(", ")
                    inner = _unwrap_node(attr)
                    if isinstance(inner, pb.String):
                        self._emit(inner.sval)
                    else:
                        self._visit_node(attr)
                self._emit(")")
        else:
            text = self._deparse_node(node)
            self._emit(text)

    # ── CREATE INDEX ──────────────────────────────────────────────

    def visit_IndexStmt(self, node: pb.IndexStmt) -> None:
        self._emit("CREATE ")
        if node.unique:
            self._emit("UNIQUE ")
        self._emit("INDEX ")
        if node.concurrent:
            self._emit("CONCURRENTLY ")
        if node.if_not_exists:
            self._emit("IF NOT EXISTS ")
        if node.idxname:
            self._emit(f"{node.idxname} ")
        self._emit("ON ")
        self._visit_node(node.relation)
        if node.access_method and node.access_method != "btree":
            self._emit(f" USING {node.access_method}")
        self._emit(" (")
        for i, param in enumerate(node.index_params):
            if i > 0:
                self._emit(", ")
            self._visit_node(param)
        self._emit(")")
        if node.HasField("where_clause"):
            self._newline()
            self._emit("WHERE")
            self._newline()
            self._indent()
            self._visit_where_expr(node.where_clause)
            self._dedent()

    def visit_IndexElem(self, node: pb.IndexElem) -> None:
        if node.name:
            self._emit(node.name)
        elif node.HasField("expr"):
            self._visit_node(node.expr)
        if node.ordering == pb.SORTBY_ASC:
            self._emit(" ASC")
        elif node.ordering == pb.SORTBY_DESC:
            self._emit(" DESC")
        if node.nulls_ordering == pb.SORTBY_NULLS_FIRST:
            self._emit(" NULLS FIRST")
        elif node.nulls_ordering == pb.SORTBY_NULLS_LAST:
            self._emit(" NULLS LAST")

    # ── CREATE VIEW ───────────────────────────────────────────────

    def visit_ViewStmt(self, node: pb.ViewStmt) -> None:
        self._emit("CREATE ")
        if node.replace:
            self._emit("OR REPLACE ")
        self._emit("VIEW ")
        self._visit_node(node.view)
        if node.aliases:
            self._emit(" (")
            for i, alias in enumerate(node.aliases):
                if i > 0:
                    self._emit(", ")
                inner = _unwrap_node(alias)
                if isinstance(inner, pb.String):
                    self._emit(inner.sval)
                else:
                    self._visit_node(alias)
            self._emit(")")
        self._emit(" AS")
        self._newline()
        self._visit_node(node.query)

    # ── ALTER TABLE ───────────────────────────────────────────────

    def visit_AlterTableStmt(self, node: pb.AlterTableStmt) -> None:
        obj_type = "TABLE"
        if node.objtype == pb.OBJECT_INDEX:
            obj_type = "INDEX"
        elif node.objtype == pb.OBJECT_VIEW:
            obj_type = "VIEW"
        elif node.objtype == pb.OBJECT_SEQUENCE:
            obj_type = "SEQUENCE"

        self._emit(f"ALTER {obj_type} ")
        if node.missing_ok:
            self._emit("IF EXISTS ")
        self._visit_node(node.relation)

        for i, cmd_node in enumerate(node.cmds):
            if i > 0:
                self._emit(",")
            self._newline()
            self._indent()
            cmd = _unwrap_node(cmd_node)
            self._visit_alter_table_cmd(cmd)
            self._dedent()

    def _visit_alter_table_cmd(self, node: Message) -> None:
        cmd = cast("pb.AlterTableCmd", node)
        subtype = cmd.subtype
        if subtype == pb.AT_AddColumn:
            self._emit("ADD COLUMN ")
            if cmd.HasField("def"):
                inner = _unwrap_node(getattr(cmd, "def"))
                if isinstance(inner, pb.ColumnDef):
                    self._visit_column_def(inner)
                else:
                    self._visit_node(inner)
            elif cmd.name:
                self._emit(cmd.name)
        elif subtype == pb.AT_DropColumn:
            self._emit(f"DROP COLUMN {cmd.name}")
            if cmd.behavior == pb.DROP_CASCADE:
                self._emit(" CASCADE")
        elif subtype == pb.AT_AlterColumnType:
            self._emit(f"ALTER COLUMN {cmd.name} TYPE")
        elif subtype == pb.AT_ColumnDefault:
            self._emit(f"ALTER COLUMN {cmd.name}")
            # Has a def field → SET DEFAULT; otherwise DROP DEFAULT
            self._emit(" SET DEFAULT" if cmd.HasField("def") else " DROP DEFAULT")
        elif subtype == pb.AT_SetNotNull:
            self._emit(f"ALTER COLUMN {cmd.name} SET NOT NULL")
        elif subtype == pb.AT_DropNotNull:
            self._emit(f"ALTER COLUMN {cmd.name} DROP NOT NULL")
        elif subtype == pb.AT_AddConstraint:
            self._emit("ADD ")
            if cmd.HasField("def"):
                inner = _unwrap_node(getattr(cmd, "def"))
                if isinstance(inner, pb.Constraint):
                    self._visit_constraint(inner)
                else:
                    self._visit_node(inner)
        else:
            # Fallback: deparse the whole ALTER TABLE statement
            text = self._deparse_node(cmd)
            self._emit(text)

    # ── DROP ──────────────────────────────────────────────────────

    def visit_DropStmt(self, node: pb.DropStmt) -> None:
        obj_type_map = {
            pb.OBJECT_TABLE: "TABLE",
            pb.OBJECT_INDEX: "INDEX",
            pb.OBJECT_VIEW: "VIEW",
            pb.OBJECT_SEQUENCE: "SEQUENCE",
            pb.OBJECT_SCHEMA: "SCHEMA",
            pb.OBJECT_TYPE: "TYPE",
            pb.OBJECT_FUNCTION: "FUNCTION",
            pb.OBJECT_MATVIEW: "MATERIALIZED VIEW",
        }
        obj_type = obj_type_map.get(node.remove_type, "TABLE")
        self._emit(f"DROP {obj_type} ")
        if node.missing_ok:
            self._emit("IF EXISTS ")
        for i, obj_node in enumerate(node.objects):
            if i > 0:
                self._emit(", ")
            inner = _unwrap_node(obj_node)
            if isinstance(inner, pb.List):
                # Multi-part name like schema.table
                parts = [cast("pb.String", _unwrap_node(n)).sval for n in inner.items]
                self._emit(".".join(parts))
            elif isinstance(inner, pb.String):
                self._emit(inner.sval)
            else:
                self._visit_node(obj_node)
        if node.behavior == pb.DROP_CASCADE:
            self._emit(" CASCADE")
        elif node.behavior == pb.DROP_RESTRICT:
            self._emit(" RESTRICT")

    # ── Misc helpers ──────────────────────────────────────────────

    def visit_String(self, node: pb.String) -> None:
        self._emit(node.sval)

    def visit_Integer(self, node: pb.Integer) -> None:
        self._emit(str(node.ival))

    def visit_Float(self, node: pb.Float) -> None:
        self._emit(node.fval)

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
            self._emit(f" AS {node.alias.aliasname}")
            if node.alias.colnames:
                self._emit("(")
                for i, cn in enumerate(node.alias.colnames):
                    if i > 0:
                        self._emit(", ")
                    col = _unwrap_node(cn)
                    if isinstance(col, pb.String):
                        self._emit(col.sval)
                    else:
                        self._visit_node(cn)
                self._emit(")")

    def visit_ColumnDef(self, node: pb.ColumnDef) -> None:
        self._visit_column_def(node)
