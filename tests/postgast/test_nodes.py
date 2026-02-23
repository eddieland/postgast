"""Tests for typed AST wrapper classes."""

from __future__ import annotations

import postgast
from postgast.nodes import (
    A_Const,
    A_Expr,
    AstNode,
    ColumnRef,
    CreateStmt,
    DeleteStmt,
    FuncCall,
    InsertStmt,
    RangeVar,
    RawStmt,
    ResTarget,
    SelectStmt,
    UpdateStmt,
    wrap,
)


def _parse_wrap(sql: str) -> AstNode:
    """Parse SQL and wrap the result."""
    return wrap(postgast.parse(sql))


def _first_stmt(sql: str) -> AstNode:
    """Parse SQL, wrap, and return the inner statement."""
    tree = _parse_wrap(sql)
    return tree.stmts[0].stmt


class TestWrapDispatch:
    """wrap() produces the correct wrapper type for major node types."""

    def test_select_stmt(self) -> None:
        stmt = _first_stmt("SELECT 1")
        assert isinstance(stmt, SelectStmt)

    def test_insert_stmt(self) -> None:
        stmt = _first_stmt("INSERT INTO t VALUES (1)")
        assert isinstance(stmt, InsertStmt)

    def test_delete_stmt(self) -> None:
        stmt = _first_stmt("DELETE FROM t")
        assert isinstance(stmt, DeleteStmt)

    def test_update_stmt(self) -> None:
        stmt = _first_stmt("UPDATE t SET x = 1")
        assert isinstance(stmt, UpdateStmt)

    def test_create_stmt(self) -> None:
        stmt = _first_stmt("CREATE TABLE t (id int)")
        assert isinstance(stmt, CreateStmt)

    def test_range_var(self) -> None:
        stmt = _first_stmt("SELECT * FROM users")
        assert isinstance(stmt, SelectStmt)
        tbl = stmt.from_clause[0]
        assert isinstance(tbl, RangeVar)

    def test_column_ref(self) -> None:
        stmt = _first_stmt("SELECT name FROM users")
        target = stmt.target_list[0]
        assert isinstance(target, ResTarget)
        assert isinstance(target.val, ColumnRef)

    def test_a_expr(self) -> None:
        stmt = _first_stmt("SELECT * FROM t WHERE x = 1")
        assert isinstance(stmt.where_clause, A_Expr)

    def test_func_call(self) -> None:
        stmt = _first_stmt("SELECT count(*) FROM t")
        target = stmt.target_list[0]
        assert isinstance(target.val, FuncCall)

    def test_a_const(self) -> None:
        stmt = _first_stmt("SELECT 42")
        target = stmt.target_list[0]
        assert isinstance(target.val, A_Const)


class TestNodeOneofUnwrapping:
    """Node oneof wrappers are transparently unwrapped."""

    def test_stmt_unwrapped(self) -> None:
        tree = _parse_wrap("SELECT 1")
        raw_stmt = tree.stmts[0]
        assert isinstance(raw_stmt, RawStmt)
        # stmt field is a Node oneof in protobuf, should be unwrapped
        inner = raw_stmt.stmt
        assert isinstance(inner, SelectStmt)
        assert type(inner).__name__ != "Node"

    def test_where_clause_unwrapped(self) -> None:
        stmt = _first_stmt("SELECT * FROM t WHERE x = 1")
        where = stmt.where_clause
        assert isinstance(where, A_Expr)


class TestScalarFieldAccess:
    """Scalar fields return the correct Python types."""

    def test_relname_string(self) -> None:
        stmt = _first_stmt("SELECT * FROM users")
        tbl = stmt.from_clause[0]
        assert isinstance(tbl, RangeVar)
        assert tbl.relname == "users"
        assert isinstance(tbl.relname, str)

    def test_stmt_location_int(self) -> None:
        tree = _parse_wrap("SELECT 1")
        raw_stmt = tree.stmts[0]
        assert isinstance(raw_stmt, RawStmt)
        assert isinstance(raw_stmt.stmt_location, int)
        assert raw_stmt.stmt_location == 0


class TestConcreteMessageFieldAccess:
    """Concrete message fields return the correct wrapper type."""

    def test_insert_relation(self) -> None:
        stmt = _first_stmt("INSERT INTO t VALUES (1)")
        assert isinstance(stmt, InsertStmt)
        assert isinstance(stmt.relation, RangeVar)
        assert stmt.relation.relname == "t"


class TestPolymorphicFieldAccess:
    """Polymorphic (Node) fields return an AstNode subclass."""

    def test_where_clause_is_ast_node(self) -> None:
        stmt = _first_stmt("SELECT * FROM t WHERE x = 1")
        where = stmt.where_clause
        assert isinstance(where, AstNode)
        assert isinstance(where, A_Expr)

    def test_unset_where_clause_is_none(self) -> None:
        stmt = _first_stmt("SELECT 1")
        assert isinstance(stmt, SelectStmt)
        assert stmt.where_clause is None


class TestRepeatedFieldAccess:
    """Repeated fields return lists."""

    def test_target_list_is_list(self) -> None:
        stmt = _first_stmt("SELECT a, b, c FROM t")
        targets = stmt.target_list
        assert isinstance(targets, list)
        assert len(targets) == 3
        assert all(isinstance(t, AstNode) for t in targets)

    def test_empty_repeated_field(self) -> None:
        stmt = _first_stmt("SELECT 1")
        assert isinstance(stmt, SelectStmt)
        assert stmt.from_clause == []


class TestPatternMatching:
    """Structural pattern matching works with wrappers."""

    def test_match_select_stmt(self) -> None:
        stmt = _first_stmt("SELECT 1")
        matched = False
        match stmt:
            case SelectStmt():
                matched = True
        assert matched

    def test_match_with_field_extraction(self) -> None:
        stmt = _first_stmt("SELECT * FROM users WHERE active")
        match stmt:
            case SelectStmt(from_clause=tables, where_clause=where):
                assert len(tables) == 1
                assert isinstance(tables[0], RangeVar)
                assert where is not None
            case _:
                raise AssertionError("Should have matched SelectStmt")

    def test_match_insert(self) -> None:
        stmt = _first_stmt("INSERT INTO t VALUES (1)")
        match stmt:
            case InsertStmt(relation=RangeVar() as rv):
                assert rv.relname == "t"
            case _:
                raise AssertionError("Should have matched InsertStmt")

    def test_match_multiple_cases(self) -> None:
        results = []
        for sql in ["SELECT 1", "INSERT INTO t VALUES (1)", "DELETE FROM t"]:
            stmt = _first_stmt(sql)
            match stmt:
                case SelectStmt():
                    results.append("select")
                case InsertStmt():
                    results.append("insert")
                case DeleteStmt():
                    results.append("delete")
        assert results == ["select", "insert", "delete"]


class TestReprAndEquality:
    """__repr__, __eq__, and __hash__ work correctly."""

    def test_repr(self) -> None:
        stmt = _first_stmt("SELECT 1")
        assert repr(stmt) == "SelectStmt(...)"

    def test_eq_same_pb(self) -> None:
        tree = postgast.parse("SELECT 1")
        a = wrap(tree)
        b = wrap(tree)
        assert a == b

    def test_eq_different_pb(self) -> None:
        a = _parse_wrap("SELECT 1")
        b = _parse_wrap("SELECT 2")
        assert a != b

    def test_hash_identity_based(self) -> None:
        tree = postgast.parse("SELECT 1")
        a = wrap(tree)
        b = wrap(tree)
        # hash is identity-based, so same pb gives same hash
        assert hash(a) == hash(b)


class TestRoundtrip:
    """Wrapper preserves the original protobuf message."""

    def test_pb_attribute(self) -> None:
        tree = postgast.parse("SELECT 1")
        wrapped = wrap(tree)
        assert wrapped._pb is tree

    def test_wrap_idempotent(self) -> None:
        wrapped = _parse_wrap("SELECT 1")
        double_wrapped = wrap(wrapped)
        assert double_wrapped is wrapped
