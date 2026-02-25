"""Convenience functions for extracting common information from parsed SQL ASTs."""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, TypeVar

from google.protobuf.message import Message

from postgast.pg_query_pb2 import (
    FUNC_PARAM_DEFAULT,
    FUNC_PARAM_IN,
    FUNC_PARAM_INOUT,
    FUNC_PARAM_VARIADIC,
    OBJECT_FUNCTION,
    OBJECT_INDEX,
    OBJECT_MATVIEW,
    OBJECT_PROCEDURE,
    OBJECT_SCHEMA,
    OBJECT_SEQUENCE,
    OBJECT_TABLE,
    OBJECT_TRIGGER,
    OBJECT_TYPE,
    OBJECT_VIEW,
    A_Star,
    ColumnRef,
    CreateExtensionStmt,
    CreateFunctionStmt,
    CreateSchemaStmt,
    CreateSeqStmt,
    CreateStmt,
    CreateTableAsStmt,
    CreateTrigStmt,
    DropStmt,
    FuncCall,
    IndexStmt,
    Node,
    ObjectWithArgs,
    ParseResult,
    RangeVar,
    String,
    ViewStmt,
)
from postgast.walk import walk

if TYPE_CHECKING:
    from collections.abc import Generator

    from postgast.pg_query_pb2 import ObjectType

_M = TypeVar("_M", bound=Message)
_OR_REPLACE_TYPES = (CreateFunctionStmt, CreateTrigStmt, ViewStmt)
_IF_NOT_EXISTS_TYPES = (CreateStmt, IndexStmt, CreateSeqStmt, CreateSchemaStmt, CreateExtensionStmt, CreateTableAsStmt)


class FunctionIdentity(typing.NamedTuple):
    """Identity parts of a ``CREATE FUNCTION`` statement.

    Attributes:
        schema: Schema name, or ``None`` for unqualified functions.
        name: Function name.
    """

    schema: str | None
    name: str


class TriggerIdentity(typing.NamedTuple):
    """Identity parts of a ``CREATE TRIGGER`` statement.

    Attributes:
        trigger: Trigger name.
        schema: Schema qualifying the target table, or ``None``.
        table: Target table name.
    """

    trigger: str
    schema: str | None
    table: str


def find_nodes(tree: Message, node_type: type[_M]) -> Generator[_M, None, None]:
    """Yield all protobuf messages matching *node_type* from a parse tree.

    Walks the tree in depth-first pre-order (same as :func:`walk`) and yields every message that is an instance of
    *node_type*.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).
        node_type: Protobuf message class to match (e.g., ``RangeVar``).

    Yields:
        Matching instances in depth-first pre-order.

    Example:
        >>> from postgast import find_nodes, parse
        >>> from postgast.pg_query_pb2 import RangeVar
        >>> tree = parse("SELECT * FROM users JOIN orders ON users.id = orders.uid")
        >>> [n.relname for n in find_nodes(tree, RangeVar)]
        ['users', 'orders']
    """
    for _field_name, node in walk(tree):
        if isinstance(node, node_type):
            yield node


def extract_tables(tree: Message) -> list[str]:
    """Return table names referenced in a parse tree.

    Collects all ``RangeVar`` nodes and returns their names as dot-joined strings (``"schema.table"`` when
    schema-qualified, ``"table"`` otherwise).

    Results preserve encounter order and include duplicates. Use ``set()`` on the result to get unique table names.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        Table names in encounter order.

    Example:
        >>> from postgast import extract_tables, parse
        >>> tree = parse("SELECT * FROM public.users JOIN orders ON true")
        >>> extract_tables(tree)
        ['public.users', 'orders']
    """
    return [
        f"{node.schemaname}.{node.relname}" if node.schemaname else node.relname for node in find_nodes(tree, RangeVar)
    ]


def extract_columns(tree: Message) -> list[str]:
    """Return column references found in a parse tree.

    Collects all ``ColumnRef`` nodes and returns their names as dot-joined strings. ``SELECT *`` produces ``"*"``;
    ``t.*`` produces ``"t.*"``.

    Results preserve encounter order and include duplicates.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        Column references in encounter order.

    Example:
        >>> from postgast import extract_columns, parse
        >>> tree = parse("SELECT u.name, age FROM users u WHERE age > 18")
        >>> extract_columns(tree)
        ['u.name', 'age', 'age']
    """
    columns: list[str] = []
    for node in find_nodes(tree, ColumnRef):
        parts: list[str] = []
        for field_node in node.fields:
            which = field_node.WhichOneof("node")
            if which is not None:
                inner = getattr(field_node, which)
                if isinstance(inner, String):
                    parts.append(inner.sval)
                elif isinstance(inner, A_Star):
                    parts.append("*")
        columns.append(".".join(parts))
    return columns


def extract_functions(tree: Message) -> list[str]:
    """Return function call names found in a parse tree.

    Collects all ``FuncCall`` nodes and returns their names as dot-joined strings (``"schema.func"`` when
    schema-qualified, ``"func"`` otherwise).

    Results preserve encounter order and include duplicates.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        Function names in encounter order.

    Example:
        >>> from postgast import extract_functions, parse
        >>> tree = parse("SELECT lower(name), count(*) FROM users")
        >>> extract_functions(tree)
        ['lower', 'count']
    """
    functions: list[str] = []
    for node in find_nodes(tree, FuncCall):
        parts: list[str] = []
        for name_node in node.funcname:
            which = name_node.WhichOneof("node")
            if which is not None:
                inner = getattr(name_node, which)
                if isinstance(inner, String):
                    parts.append(inner.sval)
        functions.append(".".join(parts))
    return functions


def extract_function_identity(tree: Message) -> FunctionIdentity | None:
    """Return the identity of the first ``CREATE FUNCTION`` statement in a parse tree.

    Finds the first ``CreateFunctionStmt`` node where ``is_procedure`` is ``False`` and returns a
    :class:`FunctionIdentity` with the schema and function name.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        A :class:`FunctionIdentity` or ``None`` if no matching node is found.

    Example:
        >>> from postgast import extract_function_identity, parse
        >>> sql = "CREATE FUNCTION public.add(a int, b int) RETURNS int LANGUAGE sql AS $$ SELECT a + b $$"
        >>> identity = extract_function_identity(parse(sql))
        >>> identity.schema, identity.name
        ('public', 'add')
    """
    for node in find_nodes(tree, CreateFunctionStmt):
        if node.is_procedure:
            continue
        parts: list[str] = []
        for name_node in node.funcname:
            which = name_node.WhichOneof("node")
            if which is not None:
                inner = getattr(name_node, which)
                if isinstance(inner, String):
                    parts.append(inner.sval)
        if len(parts) == 2:
            return FunctionIdentity(schema=parts[0], name=parts[1])
        if len(parts) == 1:
            return FunctionIdentity(schema=None, name=parts[0])
    return None


def extract_trigger_identity(tree: Message) -> TriggerIdentity | None:
    """Return the identity of the first ``CREATE TRIGGER`` statement in a parse tree.

    Finds the first ``CreateTrigStmt`` node and returns a :class:`TriggerIdentity` with the trigger name, schema,
    and table name.

    Args:
        tree: Any protobuf ``Message`` (``ParseResult``, ``SelectStmt``, etc.).

    Returns:
        A :class:`TriggerIdentity` or ``None`` if no matching node is found.

    Example:
        >>> from postgast import extract_trigger_identity, parse
        >>> sql = "CREATE TRIGGER my_trg AFTER INSERT ON orders FOR EACH ROW EXECUTE FUNCTION notify()"
        >>> identity = extract_trigger_identity(parse(sql))
        >>> identity.trigger, identity.table
        ('my_trg', 'orders')
    """
    for node in find_nodes(tree, CreateTrigStmt):
        return TriggerIdentity(
            trigger=node.trigname,
            schema=node.relation.schemaname or None,
            table=node.relation.relname,
        )
    return None


def set_or_replace(tree: Message) -> int:
    """Set ``replace = True`` on eligible DDL nodes in a parse tree.

    Walks *tree* and flips the ``replace`` flag on ``CreateFunctionStmt``, ``CreateTrigStmt``, and ``ViewStmt`` nodes
    where it is currently ``False``.

    Args:
        tree: A protobuf ``Message`` (typically a ``ParseResult``).

    Returns:
        Number of nodes that were modified.

    Example:
        >>> from postgast import set_or_replace, parse, deparse
        >>> tree = parse("CREATE VIEW v AS SELECT 1")
        >>> set_or_replace(tree)
        1
        >>> "OR REPLACE" in deparse(tree)
        True
    """
    count = 0
    for _field_name, node in walk(tree):
        if isinstance(node, _OR_REPLACE_TYPES) and not node.replace:
            node.replace = True
            count += 1
    return count


def ensure_or_replace(sql: str) -> str:
    """Return *sql* with all eligible ``CREATE`` statements rewritten to ``CREATE OR REPLACE``.

    Parses the input, sets ``replace = True`` on ``CreateFunctionStmt``, ``CreateTrigStmt``, and ``ViewStmt`` nodes,
    and deparses back to SQL.

    Args:
        sql: One or more SQL statements.

    Returns:
        The rewritten SQL text.

    Raises:
        PgQueryError: If *sql* cannot be parsed.

    Example:
        >>> from postgast import ensure_or_replace
        >>> ensure_or_replace("CREATE VIEW v AS SELECT 1")
        'CREATE OR REPLACE VIEW v AS SELECT 1'
    """
    from postgast.deparse import deparse
    from postgast.parse import parse

    tree = parse(sql)
    set_or_replace(tree)
    return deparse(tree)


def set_if_not_exists(tree: Message) -> int:
    """Set ``if_not_exists = True`` on eligible DDL nodes in a parse tree.

    Walks *tree* and flips the ``if_not_exists`` flag on ``CreateStmt`` (tables), ``IndexStmt``, ``CreateSeqStmt``,
    ``CreateSchemaStmt``, ``CreateExtensionStmt``, and ``CreateTableAsStmt`` nodes where it is currently ``False``.

    Args:
        tree: A protobuf ``Message`` (typically a ``ParseResult``).

    Returns:
        Number of nodes that were modified.

    Example:
        >>> from postgast import set_if_not_exists, parse, deparse
        >>> tree = parse("CREATE TABLE t (id int)")
        >>> set_if_not_exists(tree)
        1
        >>> "IF NOT EXISTS" in deparse(tree)
        True
    """
    count = 0
    for _field_name, node in walk(tree):
        if isinstance(node, _IF_NOT_EXISTS_TYPES) and not node.if_not_exists:
            node.if_not_exists = True
            count += 1
    return count


def ensure_if_not_exists(sql: str) -> str:
    """Return *sql* with all eligible ``CREATE`` statements rewritten to include ``IF NOT EXISTS``.

    Parses the input, sets ``if_not_exists = True`` on ``CREATE TABLE``, ``CREATE INDEX``, ``CREATE SEQUENCE``,
    ``CREATE SCHEMA``, ``CREATE EXTENSION``, and ``CREATE TABLE AS`` / ``CREATE MATERIALIZED VIEW ... AS`` nodes, and
    deparses back to SQL.

    Args:
        sql: One or more SQL statements.

    Returns:
        The rewritten SQL text.

    Raises:
        PgQueryError: If *sql* cannot be parsed.

    Example:
        >>> from postgast import ensure_if_not_exists
        >>> ensure_if_not_exists("CREATE TABLE t (id int)")
        'CREATE TABLE IF NOT EXISTS t (id int)'
    """
    from postgast.deparse import deparse
    from postgast.parse import parse

    tree = parse(sql)
    set_if_not_exists(tree)
    return deparse(tree)


def set_if_exists(tree: Message) -> int:
    """Set ``missing_ok = True`` on ``DropStmt`` nodes in a parse tree.

    This corresponds to the ``IF EXISTS`` clause in ``DROP`` statements. Walks *tree* and flips the ``missing_ok`` flag
    on all ``DropStmt`` nodes where it is currently ``False``.

    Args:
        tree: A protobuf ``Message`` (typically a ``ParseResult``).

    Returns:
        Number of nodes that were modified.

    Example:
        >>> from postgast import set_if_exists, parse, deparse
        >>> tree = parse("DROP TABLE t")
        >>> set_if_exists(tree)
        1
        >>> "IF EXISTS" in deparse(tree)
        True
    """
    count = 0
    for _field_name, node in walk(tree):
        if isinstance(node, DropStmt) and not node.missing_ok:
            node.missing_ok = True
            count += 1
    return count


def ensure_if_exists(sql: str) -> str:
    """Return *sql* with all ``DROP`` statements rewritten to include ``IF EXISTS``.

    Parses the input, sets ``missing_ok = True`` on all ``DropStmt`` nodes, and deparses back to SQL.

    Args:
        sql: One or more SQL statements.

    Returns:
        The rewritten SQL text.

    Raises:
        PgQueryError: If *sql* cannot be parsed.

    Example:
        >>> from postgast import ensure_if_exists
        >>> ensure_if_exists("DROP TABLE t")
        'DROP TABLE IF EXISTS t'
    """
    from postgast.deparse import deparse
    from postgast.parse import parse

    tree = parse(sql)
    set_if_exists(tree)
    return deparse(tree)


_IDENTITY_MODES = frozenset({FUNC_PARAM_IN, FUNC_PARAM_INOUT, FUNC_PARAM_VARIADIC, FUNC_PARAM_DEFAULT})


def _drop_function(stmt: CreateFunctionStmt) -> DropStmt:
    """Build a DropStmt for a CREATE FUNCTION or CREATE PROCEDURE."""
    drop = DropStmt()
    drop.remove_type = OBJECT_PROCEDURE if stmt.is_procedure else OBJECT_FUNCTION

    owa = ObjectWithArgs()
    for name_node in stmt.funcname:
        owa.objname.add().CopyFrom(name_node)
    for param_node in stmt.parameters:
        fp = param_node.function_parameter
        if fp.mode not in _IDENTITY_MODES:
            continue
        owa.objargs.add().type_name.CopyFrom(fp.arg_type)

    drop.objects.add().object_with_args.CopyFrom(owa)
    return drop


def _drop_trigger(stmt: CreateTrigStmt) -> DropStmt:
    """Build a DropStmt for a CREATE TRIGGER."""
    drop = DropStmt()
    drop.remove_type = OBJECT_TRIGGER

    lst = drop.objects.add().list
    if stmt.relation.schemaname:
        lst.items.add().string.sval = stmt.relation.schemaname
    lst.items.add().string.sval = stmt.relation.relname
    lst.items.add().string.sval = stmt.trigname
    return drop


def _drop_view(stmt: ViewStmt) -> DropStmt:
    """Build a DropStmt for a CREATE VIEW."""
    drop = DropStmt()
    drop.remove_type = OBJECT_VIEW

    lst = drop.objects.add().list
    if stmt.view.schemaname:
        lst.items.add().string.sval = stmt.view.schemaname
    lst.items.add().string.sval = stmt.view.relname
    return drop


def _drop_relation(relation: RangeVar, object_type: ObjectType) -> DropStmt:
    """Build a DropStmt for a relation-based CREATE (TABLE, INDEX, SEQUENCE)."""
    drop = DropStmt()
    drop.remove_type = object_type

    lst = drop.objects.add().list
    if relation.schemaname:
        lst.items.add().string.sval = relation.schemaname
    lst.items.add().string.sval = relation.relname
    return drop


def _drop_schema(stmt: CreateSchemaStmt) -> DropStmt:
    """Build a DropStmt for a CREATE SCHEMA."""
    drop = DropStmt()
    drop.remove_type = OBJECT_SCHEMA

    lst = drop.objects.add().list
    lst.items.add().string.sval = stmt.schemaname
    return drop


def _drop_type(type_name_nodes: typing.Any, object_type: ObjectType) -> DropStmt:
    """Build a DropStmt for a CREATE TYPE (enum, range, composite, etc.)."""
    drop = DropStmt()
    drop.remove_type = object_type

    lst = drop.objects.add().list
    for name_node in type_name_nodes:
        which = name_node.WhichOneof("node")
        if which is not None:
            inner = getattr(name_node, which)
            if isinstance(inner, String):
                lst.items.add().string.sval = inner.sval
    return drop


def to_drop(sql: str) -> str:
    """Return the ``DROP`` statement corresponding to a ``CREATE`` statement.

    Parses *sql*, builds a ``DropStmt`` protobuf from the parsed AST, and deparses it back to SQL. Supports:

    - ``CREATE FUNCTION`` / ``CREATE PROCEDURE``
    - ``CREATE TRIGGER``
    - ``CREATE VIEW``
    - ``CREATE TABLE``
    - ``CREATE INDEX``
    - ``CREATE SEQUENCE``
    - ``CREATE SCHEMA``
    - ``CREATE TYPE`` (enum, range, composite)
    - ``CREATE MATERIALIZED VIEW ... AS``

    All ``OR REPLACE`` and ``IF NOT EXISTS`` variants are accepted.

    Args:
        sql: A single CREATE statement.

    Returns:
        The corresponding DROP statement.

    Raises:
        ValueError: If *sql* contains zero or more than one statement, or if the statement is not a supported CREATE
            type.
        PgQueryError: If *sql* is not valid SQL.

    Example:
        >>> from postgast import to_drop
        >>> to_drop("CREATE TABLE public.users (id int)")
        'DROP TABLE public.users'
    """
    from postgast.deparse import deparse
    from postgast.parse import parse

    tree = parse(sql)

    if len(tree.stmts) != 1:
        msg = f"expected exactly one statement, got {len(tree.stmts)}"
        raise ValueError(msg)

    node = tree.stmts[0].stmt
    which = node.WhichOneof("node")

    if which == "create_function_stmt":
        drop = _drop_function(node.create_function_stmt)
    elif which == "create_trig_stmt":
        drop = _drop_trigger(node.create_trig_stmt)
    elif which == "view_stmt":
        drop = _drop_view(node.view_stmt)
    elif which == "create_stmt":
        drop = _drop_relation(node.create_stmt.relation, OBJECT_TABLE)
    elif which == "index_stmt":
        # Index DROP uses the index name (not the table relation)
        idx = node.index_stmt
        drop = DropStmt()
        drop.remove_type = OBJECT_INDEX
        lst = drop.objects.add().list
        if idx.relation.schemaname:
            lst.items.add().string.sval = idx.relation.schemaname
        lst.items.add().string.sval = idx.idxname
    elif which == "create_seq_stmt":
        drop = _drop_relation(node.create_seq_stmt.sequence, OBJECT_SEQUENCE)
    elif which == "create_schema_stmt":
        drop = _drop_schema(node.create_schema_stmt)
    elif which == "create_enum_stmt":
        drop = _drop_type(node.create_enum_stmt.type_name, OBJECT_TYPE)
    elif which == "create_range_stmt":
        drop = _drop_type(node.create_range_stmt.type_name, OBJECT_TYPE)
    elif which == "composite_type_stmt":
        drop = _drop_relation(node.composite_type_stmt.typevar, OBJECT_TYPE)
    elif which == "create_table_as_stmt":
        stmt = node.create_table_as_stmt
        if stmt.objtype == OBJECT_MATVIEW:
            drop = _drop_relation(stmt.into.rel, OBJECT_MATVIEW)
        else:
            drop = _drop_relation(stmt.into.rel, OBJECT_TABLE)
    else:
        msg = f"unsupported statement type: {which}"
        raise ValueError(msg)

    result = ParseResult()
    result.stmts.add().stmt.drop_stmt.CopyFrom(drop)
    return deparse(result)


class StatementInfo(typing.NamedTuple):
    """Classification of a SQL statement.

    Attributes:
        action: The action being performed (e.g., ``"SELECT"``, ``"CREATE"``, ``"ALTER"``, ``"DROP"``).
        object_type: The object type, if applicable (e.g., ``"TABLE"``, ``"VIEW"``, ``"FUNCTION"``).
            ``None`` for DML statements like ``SELECT`` or ``INSERT``.
        node_name: The protobuf oneof field name (e.g., ``"select_stmt"``, ``"create_stmt"``).
    """

    action: str
    object_type: str | None
    node_name: str


# Mapping from protobuf oneof field name to (action, object_type).
_STATEMENT_CLASSIFICATION: dict[str, tuple[str, str | None]] = {
    # DML
    "select_stmt": ("SELECT", None),
    "insert_stmt": ("INSERT", None),
    "update_stmt": ("UPDATE", None),
    "delete_stmt": ("DELETE", None),
    "merge_stmt": ("MERGE", None),
    # DDL — CREATE
    "create_stmt": ("CREATE", "TABLE"),
    "view_stmt": ("CREATE", "VIEW"),
    "index_stmt": ("CREATE", "INDEX"),
    "create_function_stmt": ("CREATE", "FUNCTION"),  # may also be PROCEDURE, refined below
    "create_trig_stmt": ("CREATE", "TRIGGER"),
    "create_seq_stmt": ("CREATE", "SEQUENCE"),
    "create_schema_stmt": ("CREATE", "SCHEMA"),
    "create_enum_stmt": ("CREATE", "TYPE"),
    "create_range_stmt": ("CREATE", "TYPE"),
    "composite_type_stmt": ("CREATE", "TYPE"),
    "create_domain_stmt": ("CREATE", "DOMAIN"),
    "create_extension_stmt": ("CREATE", "EXTENSION"),
    "createdb_stmt": ("CREATE", "DATABASE"),
    "create_role_stmt": ("CREATE", "ROLE"),
    "create_table_as_stmt": ("CREATE", "TABLE"),  # may also be MATERIALIZED VIEW, refined below
    "create_policy_stmt": ("CREATE", "POLICY"),
    "create_publication_stmt": ("CREATE", "PUBLICATION"),
    "create_subscription_stmt": ("CREATE", "SUBSCRIPTION"),
    "create_foreign_table_stmt": ("CREATE", "FOREIGN TABLE"),
    "create_foreign_server_stmt": ("CREATE", "SERVER"),
    "create_fdw_stmt": ("CREATE", "FOREIGN DATA WRAPPER"),
    "create_table_space_stmt": ("CREATE", "TABLESPACE"),
    "create_conversion_stmt": ("CREATE", "CONVERSION"),
    "create_cast_stmt": ("CREATE", "CAST"),
    "create_op_class_stmt": ("CREATE", "OPERATOR CLASS"),
    "create_op_family_stmt": ("CREATE", "OPERATOR FAMILY"),
    "create_plang_stmt": ("CREATE", "LANGUAGE"),
    "create_transform_stmt": ("CREATE", "TRANSFORM"),
    "create_am_stmt": ("CREATE", "ACCESS METHOD"),
    "create_event_trig_stmt": ("CREATE", "EVENT TRIGGER"),
    "create_stats_stmt": ("CREATE", "STATISTICS"),
    "create_user_mapping_stmt": ("CREATE", "USER MAPPING"),
    "rule_stmt": ("CREATE", "RULE"),
    # DDL — ALTER
    "alter_table_stmt": ("ALTER", "TABLE"),
    "alter_domain_stmt": ("ALTER", "DOMAIN"),
    "alter_function_stmt": ("ALTER", "FUNCTION"),
    "alter_role_stmt": ("ALTER", "ROLE"),
    "alter_role_set_stmt": ("ALTER", "ROLE"),
    "alter_database_stmt": ("ALTER", "DATABASE"),
    "alter_database_set_stmt": ("ALTER", "DATABASE"),
    "alter_database_refresh_coll_stmt": ("ALTER", "DATABASE"),
    "alter_seq_stmt": ("ALTER", "SEQUENCE"),
    "alter_enum_stmt": ("ALTER", "TYPE"),
    "alter_type_stmt": ("ALTER", "TYPE"),
    "alter_extension_stmt": ("ALTER", "EXTENSION"),
    "alter_extension_contents_stmt": ("ALTER", "EXTENSION"),
    "alter_event_trig_stmt": ("ALTER", "EVENT TRIGGER"),
    "alter_fdw_stmt": ("ALTER", "FOREIGN DATA WRAPPER"),
    "alter_foreign_server_stmt": ("ALTER", "SERVER"),
    "alter_user_mapping_stmt": ("ALTER", "USER MAPPING"),
    "alter_policy_stmt": ("ALTER", "POLICY"),
    "alter_publication_stmt": ("ALTER", "PUBLICATION"),
    "alter_subscription_stmt": ("ALTER", "SUBSCRIPTION"),
    "alter_op_family_stmt": ("ALTER", "OPERATOR FAMILY"),
    "alter_operator_stmt": ("ALTER", "OPERATOR"),
    "alter_collation_stmt": ("ALTER", "COLLATION"),
    "alter_system_stmt": ("ALTER", "SYSTEM"),
    "alter_table_space_options_stmt": ("ALTER", "TABLESPACE"),
    "alter_table_move_all_stmt": ("ALTER", "TABLE"),
    "alter_owner_stmt": ("ALTER", "OWNER"),
    "alter_object_schema_stmt": ("ALTER", "SCHEMA"),
    "alter_object_depends_stmt": ("ALTER", "DEPENDS"),
    "alter_default_privileges_stmt": ("ALTER", "DEFAULT PRIVILEGES"),
    "alter_tsdictionary_stmt": ("ALTER", "TEXT SEARCH DICTIONARY"),
    "alter_tsconfiguration_stmt": ("ALTER", "TEXT SEARCH CONFIGURATION"),
    "alter_stats_stmt": ("ALTER", "STATISTICS"),
    "rename_stmt": ("ALTER", "RENAME"),
    # DDL — DROP
    "drop_stmt": ("DROP", None),  # refined below from remove_type
    "dropdb_stmt": ("DROP", "DATABASE"),
    "drop_role_stmt": ("DROP", "ROLE"),
    "drop_subscription_stmt": ("DROP", "SUBSCRIPTION"),
    "drop_table_space_stmt": ("DROP", "TABLESPACE"),
    "drop_user_mapping_stmt": ("DROP", "USER MAPPING"),
    "drop_owned_stmt": ("DROP", "OWNED"),
    # DDL — GRANT / REVOKE
    "grant_stmt": ("GRANT", None),  # refined below
    "grant_role_stmt": ("GRANT", "ROLE"),
    # DDL — other
    "truncate_stmt": ("TRUNCATE", "TABLE"),
    "comment_stmt": ("COMMENT", None),
    "sec_label_stmt": ("SECURITY LABEL", None),
    "refresh_mat_view_stmt": ("REFRESH", "MATERIALIZED VIEW"),
    "reassign_owned_stmt": ("REASSIGN", "OWNED"),
    "reindex_stmt": ("REINDEX", None),
    "cluster_stmt": ("CLUSTER", None),
    "vacuum_stmt": ("VACUUM", None),
    # Transaction control
    "transaction_stmt": ("TRANSACTION", None),
    # Session / misc
    "explain_stmt": ("EXPLAIN", None),
    "prepare_stmt": ("PREPARE", None),
    "execute_stmt": ("EXECUTE", None),
    "deallocate_stmt": ("DEALLOCATE", None),
    "copy_stmt": ("COPY", None),
    "do_stmt": ("DO", None),
    "call_stmt": ("CALL", None),
    "variable_set_stmt": ("SET", None),
    "variable_show_stmt": ("SHOW", None),
    "lock_stmt": ("LOCK", None),
    "listen_stmt": ("LISTEN", None),
    "unlisten_stmt": ("UNLISTEN", None),
    "notify_stmt": ("NOTIFY", None),
    "load_stmt": ("LOAD", None),
    "discard_stmt": ("DISCARD", None),
    "fetch_stmt": ("FETCH", None),
    "declare_cursor_stmt": ("DECLARE", "CURSOR"),
    "close_portal_stmt": ("CLOSE", "CURSOR"),
    "check_point_stmt": ("CHECKPOINT", None),
    "constraints_set_stmt": ("SET CONSTRAINTS", None),
    "import_foreign_schema_stmt": ("IMPORT", "FOREIGN SCHEMA"),
    "set_operation_stmt": ("SELECT", None),
    "define_stmt": ("CREATE", None),
    "replica_identity_stmt": ("ALTER", "TABLE"),
}

# Mapping from DropStmt.remove_type to human-readable object type.
_DROP_OBJECT_TYPES: dict[int, str] = {
    OBJECT_TABLE: "TABLE",
    OBJECT_VIEW: "VIEW",
    OBJECT_INDEX: "INDEX",
    OBJECT_SEQUENCE: "SEQUENCE",
    OBJECT_SCHEMA: "SCHEMA",
    OBJECT_TYPE: "TYPE",
    OBJECT_FUNCTION: "FUNCTION",
    OBJECT_PROCEDURE: "PROCEDURE",
    OBJECT_TRIGGER: "TRIGGER",
    OBJECT_MATVIEW: "MATERIALIZED VIEW",
}


def classify_statement(tree: ParseResult | Node) -> StatementInfo | None:
    """Classify the first statement in a parse tree.

    Returns a :class:`StatementInfo` describing the action (``SELECT``, ``CREATE``, ``ALTER``, ``DROP``, etc.) and
    object type (``TABLE``, ``VIEW``, ``FUNCTION``, etc.) of the first statement in *tree*.

    Args:
        tree: A ``ParseResult`` or a ``Node`` wrapping a statement.

    Returns:
        A :class:`StatementInfo`, or ``None`` if the tree contains no statements.

    Example:
        >>> from postgast import classify_statement, parse
        >>> info = classify_statement(parse("CREATE TABLE t (id int)"))
        >>> info.action, info.object_type
        ('CREATE', 'TABLE')
    """
    if isinstance(tree, ParseResult):
        if not tree.stmts:
            return None
        node = tree.stmts[0].stmt
    else:
        node = tree

    which = node.WhichOneof("node")
    if which is None:
        return None

    entry = _STATEMENT_CLASSIFICATION.get(which)
    if entry is None:
        return StatementInfo(action="UNKNOWN", object_type=None, node_name=which)

    action, object_type = entry

    # Refine CREATE FUNCTION vs CREATE PROCEDURE
    if which == "create_function_stmt" and node.create_function_stmt.is_procedure:
        object_type = "PROCEDURE"

    # Refine CREATE TABLE AS vs CREATE MATERIALIZED VIEW AS
    if which == "create_table_as_stmt" and node.create_table_as_stmt.objtype == OBJECT_MATVIEW:
        object_type = "MATERIALIZED VIEW"

    # Refine DropStmt using remove_type
    if which == "drop_stmt":
        object_type = _DROP_OBJECT_TYPES.get(node.drop_stmt.remove_type)

    # Refine GRANT vs REVOKE
    if which == "grant_stmt":
        action = "GRANT" if node.grant_stmt.is_grant else "REVOKE"

    return StatementInfo(action=action, object_type=object_type, node_name=which)
