from __future__ import annotations

from google.protobuf.message import Message

from postgast import ParseResult, Visitor, parse, walk


class TestWalk:
    def test_simple_select(self, select1_tree: ParseResult):
        """4.1: walk yields ParseResult, RawStmt, and SelectStmt with correct field names."""
        nodes = list(walk(select1_tree))

        type_names = [type(msg).DESCRIPTOR.name for _, msg in nodes]
        assert type_names[0] == "ParseResult"
        assert "RawStmt" in type_names
        assert "SelectStmt" in type_names

        # Root has empty field name
        assert nodes[0][0] == ""

        # RawStmt comes from "stmts" field
        raw_stmt_entry = next((fn, msg) for fn, msg in nodes if type(msg).DESCRIPTOR.name == "RawStmt")
        assert raw_stmt_entry[0] == "stmts"

    def test_field_names(self):
        """4.2: walk yields correct field names for SELECT a FROM t WHERE x = 1."""
        result = parse("SELECT a FROM t WHERE x = 1")
        field_names = [fn for fn, _ in walk(result)]

        assert "stmts" in field_names
        assert "where_clause" in field_names
        assert "target_list" in field_names
        assert "from_clause" in field_names

    def test_walk_subtree(self, select1_tree: ParseResult):
        """4.3: walk on a SelectStmt starts with ("", SelectStmt)."""
        select_stmt = select1_tree.stmts[0].stmt.select_stmt
        nodes = list(walk(select_stmt))

        assert nodes[0][0] == ""
        assert type(nodes[0][1]).DESCRIPTOR.name == "SelectStmt"

    def test_multi_statement(self):
        """4.4: walk on multi-statement input covers both statements."""
        result = parse("SELECT 1; CREATE TABLE t (id int)")
        type_names = [type(msg).DESCRIPTOR.name for _, msg in walk(result)]

        assert "SelectStmt" in type_names
        assert "CreateStmt" in type_names

    def test_no_node_wrappers(self):
        """4.5: no Node wrapper messages appear in walk output."""
        result = parse("SELECT a FROM t WHERE x = 1")
        for _, msg in walk(result):
            assert type(msg).DESCRIPTOR.name != "Node"

    def test_scalar_fields_not_yielded(self, select1_tree: ParseResult):
        """4.6: scalar fields (strings, ints, enums) are not yielded by walk."""
        for _, msg in walk(select1_tree):
            # Every yielded value should be a protobuf Message, not a scalar
            assert hasattr(msg, "DESCRIPTOR"), f"Expected Message, got {type(msg)}"
            assert hasattr(msg, "ListFields"), f"Expected Message, got {type(msg)}"


class TestVisitor:
    def test_dispatch_to_visit_select_stmt(self, select1_tree: ParseResult):
        """4.7: Visitor dispatches to visit_SelectStmt when defined."""
        visited: list[Message] = []

        class V(Visitor):
            def visit_SelectStmt(self, node: Message) -> None:
                visited.append(node)

        V().visit(select1_tree)
        assert len(visited) == 1
        assert type(visited[0]).DESCRIPTOR.name == "SelectStmt"

    def test_fallback_to_generic_visit(self, select1_tree: ParseResult):
        """4.8: Visitor falls back to generic_visit when no specific handler is defined."""
        visited_types: list[str] = []

        class V(Visitor):
            def generic_visit(self, node: Message) -> None:  # pyright: ignore[reportImplicitOverride]
                visited_types.append(type(node).DESCRIPTOR.name)
                super().generic_visit(node)

        V().visit(select1_tree)
        # generic_visit should have been called for multiple node types
        assert "ParseResult" in visited_types
        assert "RawStmt" in visited_types
        assert "SelectStmt" in visited_types

    def test_no_generic_visit_skips_children(self):
        """4.9: defining visit_SelectStmt without calling generic_visit skips children."""
        visited_types: list[str] = []

        class V(Visitor):
            def visit_SelectStmt(self, _node: Message) -> None:
                visited_types.append("SelectStmt")
                # Deliberately NOT calling self.generic_visit(node)

            def visit_ResTarget(self, _node: Message) -> None:
                visited_types.append("ResTarget")

        result = parse("SELECT a, b FROM t")
        V().visit(result)
        assert "SelectStmt" in visited_types
        assert "ResTarget" not in visited_types  # Children skipped

    def test_generic_visit_in_handler_visits_children(self):
        """4.10: calling self.generic_visit(node) inside a handler visits children."""
        visited_types: list[str] = []

        class V(Visitor):
            def visit_SelectStmt(self, node: Message) -> None:
                visited_types.append("SelectStmt")
                self.generic_visit(node)

            def visit_ResTarget(self, _node: Message) -> None:
                visited_types.append("ResTarget")

        result = parse("SELECT a, b FROM t")
        V().visit(result)
        assert "SelectStmt" in visited_types
        assert "ResTarget" in visited_types

    def test_unwraps_node_wrappers(self):
        """4.11: Visitor unwraps Node wrappers (dispatches to visit_ColumnRef, not visit_Node)."""
        visited_types: list[str] = []

        class V(Visitor):
            def visit_ColumnRef(self, _node: Message) -> None:
                visited_types.append("ColumnRef")

            def visit_Node(self, _node: Message) -> None:
                visited_types.append("Node")

        result = parse("SELECT a FROM t")
        V().visit(result)
        assert "ColumnRef" in visited_types
        assert "Node" not in visited_types

    def test_collect_table_names(self):
        """4.12: Visitor subclass collects all table names from a JOIN query."""

        class TableCollector(Visitor):
            def __init__(self) -> None:
                self.tables: list[str] = []

            def visit_RangeVar(self, node: Message) -> None:
                self.tables.append(node.relname)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType,reportAttributeAccessIssue]

        collector = TableCollector()
        collector.visit(parse("SELECT a FROM t1 JOIN t2 ON t1.id = t2.id"))
        assert sorted(collector.tables) == ["t1", "t2"]
