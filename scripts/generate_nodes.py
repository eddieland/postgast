#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["postgast"]
# ///
"""Generate typed AST wrapper classes from the protobuf descriptor.

Usage:
    uv run scripts/generate_nodes.py

Writes to src/postgast/nodes/ package. The output is checked into version control.
"""

from __future__ import annotations

import importlib.util
import keyword
import textwrap
from pathlib import Path

from google.protobuf.descriptor import Descriptor, FieldDescriptor

# Load pg_query_pb2 directly from file to avoid triggering postgast.__init__
# (which imports nodes — the package we're generating)
_PB2_PATH = Path(__file__).resolve().parent.parent / "src" / "postgast" / "pg_query_pb2.py"
_spec = importlib.util.spec_from_file_location("pg_query_pb2", _PB2_PATH)
assert _spec is not None and _spec.loader is not None
pg_query_pb2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg_query_pb2)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src" / "postgast" / "nodes"

# Protobuf type constants
_TYPE_MESSAGE = FieldDescriptor.TYPE_MESSAGE
_TYPE_ENUM = FieldDescriptor.TYPE_ENUM
_TYPE_STRING = FieldDescriptor.TYPE_STRING
_TYPE_BOOL = FieldDescriptor.TYPE_BOOL
_TYPE_INT32 = FieldDescriptor.TYPE_INT32
_TYPE_INT64 = FieldDescriptor.TYPE_INT64
_TYPE_UINT32 = FieldDescriptor.TYPE_UINT32
_TYPE_UINT64 = FieldDescriptor.TYPE_UINT64
_TYPE_FLOAT = FieldDescriptor.TYPE_FLOAT
_TYPE_DOUBLE = FieldDescriptor.TYPE_DOUBLE
_LABEL_REPEATED = FieldDescriptor.LABEL_REPEATED

# Types to skip in __match_args__ (internal/location fields)
_SKIP_MATCH_FIELDS = {"location", "stmt_location", "stmt_len"}

# Map protobuf scalar types to Python type annotation strings
_SCALAR_TYPE_MAP: dict[int, str] = {
    _TYPE_STRING: "str",
    _TYPE_BOOL: "bool",
    _TYPE_INT32: "int",
    _TYPE_INT64: "int",
    _TYPE_UINT32: "int",
    _TYPE_UINT64: "int",
    _TYPE_FLOAT: "float",
    _TYPE_DOUBLE: "float",
}


# ---- Class docstrings ---- #
# One-line descriptions for each generated wrapper class.  Keyed by the
# wrapper class name (matches ``_wrapper_name(desc)``).  When present the
# docstring is emitted right after the ``class …(AstNode):`` line.
_CLASS_DOCSTRINGS: dict[str, str] = {
    # -- parse-tree value nodes --
    "A_ArrayExpr": "Array constructor expression (``ARRAY[...]``).",
    "A_Const": "Constant literal value (string, number, boolean, or NULL).",
    "A_Expr": "Expression with an operator (e.g. ``a + b``, ``a LIKE b``).",
    "A_Indices": "Array subscript or slice (e.g. ``[1]`` or ``[1:3]``).",
    "A_Indirection": "Indirection chain (field selection or array subscript on a value).",
    "A_Star": "Star wildcard (``*``) in a column reference or target list.",
    "AccessPriv": "Privilege name and optional column list in a ``GRANT``/``REVOKE`` statement.",
    "Aggref": "Aggregate function call (planner/executor node).",
    "Alias": "Alias for a range variable or column (``AS name(col1, col2, …)``).",
    # -- ALTER statements --
    "AlterCollationStmt": "``ALTER COLLATION`` statement.",
    "AlterDatabaseRefreshCollStmt": "``ALTER DATABASE … REFRESH COLLATION VERSION`` statement.",
    "AlterDatabaseSetStmt": "``ALTER DATABASE … SET/RESET`` configuration statement.",
    "AlterDatabaseStmt": "``ALTER DATABASE`` statement.",
    "AlterDefaultPrivilegesStmt": "``ALTER DEFAULT PRIVILEGES`` statement.",
    "AlterDomainStmt": "``ALTER DOMAIN`` statement.",
    "AlterEnumStmt": "``ALTER TYPE … ADD/RENAME VALUE`` for enum types.",
    "AlterEventTrigStmt": "``ALTER EVENT TRIGGER`` statement.",
    "AlterExtensionContentsStmt": "``ALTER EXTENSION … ADD/DROP`` object statement.",
    "AlterExtensionStmt": "``ALTER EXTENSION … UPDATE`` statement.",
    "AlterFdwStmt": "``ALTER FOREIGN DATA WRAPPER`` statement.",
    "AlterForeignServerStmt": "``ALTER SERVER`` statement.",
    "AlterFunctionStmt": "``ALTER FUNCTION/PROCEDURE/ROUTINE`` statement.",
    "AlterObjectDependsStmt": "``ALTER … DEPENDS ON EXTENSION`` statement.",
    "AlterObjectSchemaStmt": "``ALTER … SET SCHEMA`` statement.",
    "AlterOpFamilyStmt": "``ALTER OPERATOR FAMILY`` statement.",
    "AlterOperatorStmt": "``ALTER OPERATOR`` statement.",
    "AlterOwnerStmt": "``ALTER … OWNER TO`` statement.",
    "AlterPolicyStmt": "``ALTER POLICY`` statement.",
    "AlterPublicationStmt": "``ALTER PUBLICATION`` statement.",
    "AlterRoleSetStmt": "``ALTER ROLE … SET/RESET`` configuration statement.",
    "AlterRoleStmt": "``ALTER ROLE`` statement.",
    "AlterSeqStmt": "``ALTER SEQUENCE`` statement.",
    "AlterStatsStmt": "``ALTER STATISTICS`` statement.",
    "AlterSubscriptionStmt": "``ALTER SUBSCRIPTION`` statement.",
    "AlterSystemStmt": "``ALTER SYSTEM SET/RESET`` statement.",
    "AlterTSConfigurationStmt": "``ALTER TEXT SEARCH CONFIGURATION`` statement.",
    "AlterTSDictionaryStmt": "``ALTER TEXT SEARCH DICTIONARY`` statement.",
    "AlterTableCmd": "Single sub-command within an ``ALTER TABLE`` statement.",
    "AlterTableMoveAllStmt": "``ALTER TABLE ALL IN TABLESPACE … SET TABLESPACE`` statement.",
    "AlterTableSpaceOptionsStmt": "``ALTER TABLESPACE … SET/RESET`` options statement.",
    "AlterTableStmt": "``ALTER TABLE`` statement (contains a list of ``AlterTableCmd``).",
    "AlterTypeStmt": "``ALTER TYPE … SET/RESET`` attribute statement.",
    "AlterUserMappingStmt": "``ALTER USER MAPPING`` statement.",
    "AlternativeSubPlan": "Alternative sub-plan list (planner node, not produced by parser).",
    # -- planner/executor expression nodes --
    "ArrayCoerceExpr": "Array element-by-element coercion expression (planner node).",
    "ArrayExpr": "Array constructor expression (planner node).",
    "BitString": "Bit-string constant value (e.g. ``B'101'``).",
    "BoolExpr": "Boolean combination expression (``AND``, ``OR``, ``NOT``).",
    "Boolean": "Boolean constant value (``TRUE`` or ``FALSE``).",
    "BooleanTest": "``IS [NOT] TRUE/FALSE/UNKNOWN`` test expression.",
    "CTECycleClause": "``CYCLE`` clause in a recursive common table expression.",
    "CTESearchClause": "``SEARCH`` clause in a recursive common table expression.",
    "CallContext": "Context information for a ``CALL`` statement (planner node).",
    "CallStmt": "``CALL`` statement for invoking a procedure.",
    "CaseExpr": "``CASE WHEN … THEN … ELSE … END`` expression.",
    "CaseTestExpr": "Placeholder for the test value inside a ``CASE`` expression (planner node).",
    "CaseWhen": "Single ``WHEN … THEN …`` clause in a ``CASE`` expression.",
    "CheckPointStmt": "``CHECKPOINT`` statement.",
    "ClosePortalStmt": "``CLOSE`` cursor statement.",
    "ClusterStmt": "``CLUSTER`` statement.",
    "CoalesceExpr": "``COALESCE(…)`` expression.",
    "CoerceToDomain": "Coercion to a domain type with constraint checking (planner node).",
    "CoerceToDomainValue": "Placeholder for the value inside a domain check constraint (planner node).",
    "CoerceViaIO": "Coercion via I/O functions (text output then input, planner node).",
    "CollateClause": "``COLLATE`` clause attached to an expression or type.",
    "CollateExpr": "``COLLATE`` expression (planner node).",
    "ColumnDef": "Column definition in ``CREATE TABLE`` or ``ALTER TABLE ADD COLUMN``.",
    "ColumnRef": "Column reference (e.g. ``table.column`` or ``column``).",
    "CommentStmt": "``COMMENT ON`` statement.",
    "CommonTableExpr": "Common table expression (CTE) defined in a ``WITH`` clause.",
    "CompositeTypeStmt": "``CREATE TYPE … AS (…)`` composite type statement.",
    "Constraint": "Column or table constraint (``CHECK``, ``UNIQUE``, ``PRIMARY KEY``, ``FOREIGN KEY``, etc.).",
    "ConstraintsSetStmt": "``SET CONSTRAINTS`` statement.",
    "ConvertRowtypeExpr": "Row-type conversion expression (planner node).",
    # -- COPY --
    "CopyStmt": "``COPY`` statement (to/from file or program).",
    # -- CREATE statements --
    "CreateAmStmt": "``CREATE ACCESS METHOD`` statement.",
    "CreateCastStmt": "``CREATE CAST`` statement.",
    "CreateConversionStmt": "``CREATE CONVERSION`` statement.",
    "CreateDomainStmt": "``CREATE DOMAIN`` statement.",
    "CreateEnumStmt": "``CREATE TYPE … AS ENUM (…)`` statement.",
    "CreateEventTrigStmt": "``CREATE EVENT TRIGGER`` statement.",
    "CreateExtensionStmt": "``CREATE EXTENSION`` statement.",
    "CreateFdwStmt": "``CREATE FOREIGN DATA WRAPPER`` statement.",
    "CreateForeignServerStmt": "``CREATE SERVER`` statement for foreign data wrappers.",
    "CreateForeignTableStmt": "``CREATE FOREIGN TABLE`` statement.",
    "CreateFunctionStmt": "``CREATE FUNCTION/PROCEDURE/ROUTINE`` statement.",
    "CreateOpClassItem": "Single item (operator or function) in a ``CREATE OPERATOR CLASS`` statement.",
    "CreateOpClassStmt": "``CREATE OPERATOR CLASS`` statement.",
    "CreateOpFamilyStmt": "``CREATE OPERATOR FAMILY`` statement.",
    "CreatePLangStmt": "``CREATE LANGUAGE`` statement.",
    "CreatePolicyStmt": "``CREATE POLICY`` statement for row-level security.",
    "CreatePublicationStmt": "``CREATE PUBLICATION`` statement for logical replication.",
    "CreateRangeStmt": "``CREATE TYPE … AS RANGE`` statement.",
    "CreateRoleStmt": "``CREATE ROLE/USER/GROUP`` statement.",
    "CreateSchemaStmt": "``CREATE SCHEMA`` statement.",
    "CreateSeqStmt": "``CREATE SEQUENCE`` statement.",
    "CreateStatsStmt": "``CREATE STATISTICS`` statement.",
    "CreateStmt": "``CREATE TABLE`` statement.",
    "CreateSubscriptionStmt": "``CREATE SUBSCRIPTION`` statement for logical replication.",
    "CreateTableAsStmt": "``CREATE TABLE AS`` or ``SELECT INTO`` statement.",
    "CreateTableSpaceStmt": "``CREATE TABLESPACE`` statement.",
    "CreateTransformStmt": "``CREATE TRANSFORM`` statement.",
    "CreateTrigStmt": "``CREATE TRIGGER`` statement.",
    "CreateUserMappingStmt": "``CREATE USER MAPPING`` statement.",
    "CreatedbStmt": "``CREATE DATABASE`` statement.",
    # -- misc expression / utility nodes --
    "CurrentOfExpr": "``WHERE CURRENT OF cursor`` expression.",
    "DeallocateStmt": "``DEALLOCATE`` prepared statement.",
    "DeclareCursorStmt": "``DECLARE CURSOR`` statement.",
    "DefElem": "Generic name/value definition element (used in many option lists).",
    "DefineStmt": "``CREATE AGGREGATE/OPERATOR/TYPE/COLLATION`` definition statement.",
    "DeleteStmt": "``DELETE FROM`` statement.",
    "DiscardStmt": "``DISCARD`` statement (``ALL``, ``PLANS``, ``SEQUENCES``, ``TEMP``).",
    "DistinctExpr": "``IS DISTINCT FROM`` expression (planner form of a comparison).",
    "DoStmt": "``DO`` anonymous code block statement.",
    # -- DROP statements --
    "DropOwnedStmt": "``DROP OWNED BY`` statement.",
    "DropRoleStmt": "``DROP ROLE/USER/GROUP`` statement.",
    "DropStmt": "``DROP`` statement for various object types.",
    "DropSubscriptionStmt": "``DROP SUBSCRIPTION`` statement.",
    "DropTableSpaceStmt": "``DROP TABLESPACE`` statement.",
    "DropUserMappingStmt": "``DROP USER MAPPING`` statement.",
    "DropdbStmt": "``DROP DATABASE`` statement.",
    # -- EXECUTE / EXPLAIN / FETCH --
    "ExecuteStmt": "``EXECUTE`` prepared statement.",
    "ExplainStmt": "``EXPLAIN`` statement.",
    "FetchStmt": "``FETCH`` or ``MOVE`` cursor statement.",
    # -- planner expression nodes --
    "FieldSelect": "Field selection from a composite value (planner node).",
    "FieldStore": "Field assignment in a composite value update (planner node).",
    "Float": "Floating-point constant value.",
    "FromExpr": "``FROM`` clause with an optional ``WHERE`` qualification.",
    "FuncCall": "Function call in parsed SQL (e.g. ``func(args)``).",
    "FuncExpr": "Function call expression (planner node).",
    "FunctionParameter": "Parameter definition in ``CREATE FUNCTION``.",
    # -- GRANT / GROUPING --
    "GrantRoleStmt": "``GRANT/REVOKE`` role membership statement.",
    "GrantStmt": "``GRANT/REVOKE`` privileges statement.",
    "GroupingFunc": "``GROUPING(…)`` function in a query with grouping sets.",
    "GroupingSet": "``GROUPING SETS``, ``ROLLUP``, or ``CUBE`` clause.",
    # -- IMPORT / INDEX / INSERT --
    "ImportForeignSchemaStmt": "``IMPORT FOREIGN SCHEMA`` statement.",
    "IndexElem": "Single column or expression in an index definition.",
    "IndexStmt": "``CREATE INDEX`` statement.",
    "InferClause": "``ON CONFLICT`` inference clause (specifies the conflict target).",
    "InferenceElem": "Single element of an ``ON CONFLICT`` inference specification (planner node).",
    "InlineCodeBlock": "Anonymous code block for ``DO`` statement execution (planner node).",
    "InsertStmt": "``INSERT INTO`` statement.",
    "IntList": "List of integer values (internal protobuf wrapper).",
    "Integer": "Integer constant value.",
    "IntoClause": "``INTO`` clause for ``SELECT INTO`` or ``CREATE TABLE AS``.",
    # -- JOIN --
    "JoinExpr": "``JOIN`` expression (``INNER``, ``LEFT``, ``RIGHT``, ``FULL``, ``CROSS``).",
    # -- JSON / SQL/JSON --
    "JsonAggConstructor": "Common fields for JSON aggregate constructors.",
    "JsonArgument": "Named argument in a JSON constructor (``key : value``).",
    "JsonArrayAgg": "``JSON_ARRAYAGG(…)`` aggregate expression.",
    "JsonArrayConstructor": "``JSON_ARRAY(…)`` constructor expression.",
    "JsonArrayQueryConstructor": "``JSON_ARRAY(subquery)`` constructor expression.",
    "JsonBehavior": "``ON ERROR`` or ``ON EMPTY`` behavior clause in JSON functions.",
    "JsonConstructorExpr": "JSON constructor expression (planner node).",
    "JsonExpr": "JSON query expression (planner node).",
    "JsonFormat": "``FORMAT JSON`` clause specifying JSON encoding.",
    "JsonFuncExpr": "SQL/JSON function expression (``JSON_VALUE``, ``JSON_QUERY``, etc.).",
    "JsonIsPredicate": "``IS JSON`` predicate expression.",
    "JsonKeyValue": "Single ``key : value`` pair in a JSON object constructor.",
    "JsonObjectAgg": "``JSON_OBJECTAGG(…)`` aggregate expression.",
    "JsonObjectConstructor": "``JSON_OBJECT(…)`` constructor expression.",
    "JsonOutput": "Output type specification for a JSON function.",
    "JsonParseExpr": "``JSON(…)`` parse expression.",
    "JsonReturning": "``RETURNING`` clause for JSON functions.",
    "JsonScalarExpr": "``JSON_SCALAR(…)`` expression.",
    "JsonSerializeExpr": "``JSON_SERIALIZE(…)`` expression.",
    "JsonTable": "``JSON_TABLE(…)`` expression in a ``FROM`` clause.",
    "JsonTableColumn": "Column definition inside ``JSON_TABLE``.",
    "JsonTablePath": "Path specification inside ``JSON_TABLE``.",
    "JsonTablePathScan": "Path scan node inside ``JSON_TABLE`` (planner node).",
    "JsonTablePathSpec": "Path specification for ``JSON_TABLE`` with optional name.",
    "JsonTableSiblingJoin": "Sibling join between ``JSON_TABLE`` path scans (planner node).",
    "JsonValueExpr": "Expression with an associated JSON format (planner node).",
    # -- LIST / LISTEN / LOAD / LOCK --
    "List": "Generic list of nodes.",
    "ListenStmt": "``LISTEN`` statement for notification channels.",
    "LoadStmt": "``LOAD`` statement for loading shared libraries.",
    "LockStmt": "``LOCK TABLE`` statement.",
    "LockingClause": "``FOR UPDATE/SHARE/NO KEY UPDATE/KEY SHARE`` locking clause.",
    # -- MERGE --
    "MergeAction": "Single ``WHEN MATCHED/NOT MATCHED`` action in ``MERGE`` (planner node).",
    "MergeStmt": "``MERGE INTO`` statement.",
    "MergeSupportFunc": "``MERGE`` support function reference (planner node).",
    "MergeWhenClause": "``WHEN MATCHED/NOT MATCHED`` clause in a ``MERGE`` statement.",
    # -- MIN/MAX --
    "MinMaxExpr": "``GREATEST(…)`` or ``LEAST(…)`` expression.",
    "MultiAssignRef": "Reference to a specific column of a multi-assignment source.",
    # -- named arg / nextval / notify / null --
    "NamedArgExpr": "Named argument in a function call (``name => value``).",
    "NextValueExpr": "``nextval(sequence)`` expression (planner node).",
    "NotifyStmt": "``NOTIFY`` statement for sending notifications.",
    "NullIfExpr": "``NULLIF(a, b)`` expression (planner form).",
    "NullTest": "``IS [NOT] NULL`` test expression.",
    # -- object with args / OID list --
    "ObjectWithArgs": "Object name with optional argument types (used for functions/operators).",
    "OidList": "List of OID values (internal protobuf wrapper).",
    # -- ON CONFLICT --
    "OnConflictClause": "``ON CONFLICT`` clause in an ``INSERT`` statement.",
    "OnConflictExpr": "``ON CONFLICT`` expression (planner node).",
    "OpExpr": "Operator expression (planner form of an operator invocation).",
    # -- PL/pgSQL / PARAM --
    "PLAssignStmt": "PL/pgSQL assignment statement (``var := expr``).",
    "Param": "Query parameter reference (``$1``, ``$2``, etc., planner node).",
    "ParamRef": "Parameter reference (``$1``, ``$2``, etc.) in parsed SQL.",
    # -- parse / scan results --
    "ParseResult": "Top-level result of parsing SQL text (contains a list of statements).",
    "ScanResult": "Top-level result of scanning SQL text for tokens.",
    "ScanToken": "Single token from the SQL scanner.",
    # -- partition --
    "PartitionBoundSpec": "Partition bound specification (``FOR VALUES …``).",
    "PartitionCmd": "Sub-command for ``ALTER TABLE … ATTACH/DETACH PARTITION``.",
    "PartitionElem": "Single column, expression, or collation in a partition key.",
    "PartitionRangeDatum": "Single boundary value in a range partition bound.",
    "PartitionSpec": "``PARTITION BY`` specification in ``CREATE TABLE``.",
    # -- PREPARE / PUBLICATION --
    "PrepareStmt": "``PREPARE`` statement for creating a prepared statement.",
    "PublicationObjSpec": "Object specification in a ``CREATE/ALTER PUBLICATION`` statement.",
    "PublicationTable": "Table specification with optional column/row filter in a publication.",
    # -- Query (planner) --
    "Query": "Fully analyzed query tree (planner/executor node, not produced by raw parser).",
    # -- range table / range var --
    "RTEPermissionInfo": "Permission-checking information for a range table entry (planner node).",
    "RangeFunction": "Function call in a ``FROM`` clause.",
    "RangeSubselect": "Sub-``SELECT`` in a ``FROM`` clause.",
    "RangeTableFunc": "``XMLTABLE`` or similar table-valued function in ``FROM``.",
    "RangeTableFuncCol": "Column definition in a ``XMLTABLE``-style function.",
    "RangeTableSample": "``TABLESAMPLE`` clause in a ``FROM`` item.",
    "RangeTblEntry": "Range table entry (planner node representing a ``FROM`` item).",
    "RangeTblFunction": "Function call within a range table entry (planner node).",
    "RangeTblRef": "Reference to a range table entry by index (planner node).",
    "RangeVar": "Table or view reference (``schema.table``).",
    "RawStmt": "Raw statement wrapper with statement location information.",
    # -- REASSIGN / REFRESH / REINDEX / RENAME --
    "ReassignOwnedStmt": "``REASSIGN OWNED BY`` statement.",
    "RefreshMatViewStmt": "``REFRESH MATERIALIZED VIEW`` statement.",
    "ReindexStmt": "``REINDEX`` statement.",
    "RelabelType": "Type relabeling (no-op cast, planner node).",
    "RenameStmt": "``ALTER … RENAME`` statement.",
    "ReplicaIdentityStmt": "``ALTER TABLE … REPLICA IDENTITY`` statement.",
    # -- result target / return / role --
    "ResTarget": "Result target in a ``SELECT`` list, ``INSERT`` column list, or ``UPDATE SET`` clause.",
    "ReturnStmt": "``RETURN`` statement (SQL function body).",
    "RoleSpec": "Role specification (role name, ``CURRENT_USER``, ``SESSION_USER``, or ``PUBLIC``).",
    # -- row / rule --
    "RowCompareExpr": "Row-wise comparison expression (planner node).",
    "RowExpr": "``ROW(…)`` constructor expression.",
    "RowMarkClause": "Row-mark clause for locking/marking rows in a query plan.",
    "RuleStmt": "``CREATE RULE`` statement.",
    # -- SQL value function / scalar array op --
    "SQLValueFunction": "SQL-standard function requiring no arguments (e.g. ``CURRENT_TIMESTAMP``).",
    "ScalarArrayOpExpr": "Scalar operator applied to an array (``ANY``/``ALL``, planner node).",
    # -- SECURITY LABEL / SELECT --
    "SecLabelStmt": "``SECURITY LABEL`` statement.",
    "SelectStmt": "``SELECT`` statement (also used for ``VALUES`` and set operations).",
    "SetOperationStmt": "Set operation (``UNION``, ``INTERSECT``, ``EXCEPT``, planner node).",
    "SetToDefault": "``DEFAULT`` keyword used as a value in ``INSERT`` or ``UPDATE``.",
    "SinglePartitionSpec": "Single partition specification (internal).",
    # -- SORT / STATS / STRING --
    "SortBy": "``ORDER BY`` sort specification.",
    "SortGroupClause": "Sort or group clause entry referencing a target list item (planner node).",
    "StatsElem": "Column or expression element in a ``CREATE STATISTICS`` statement.",
    "String": "String constant value.",
    # -- sub-select / sub-plan / subscript --
    "SubLink": "Sub-``SELECT`` appearing in an expression (``EXISTS``, ``IN``, ``ANY``, scalar subquery, etc.).",
    "SubPlan": "Sub-plan reference in an expression (planner node).",
    "SubscriptingRef": "Array or container subscripting expression (planner node).",
    # -- summary (postgast-specific) --
    "SummaryResult": "Result of SQL summarization (tables, functions, columns referenced).",
    "SummaryResult_Table": "Table referenced in a summarized SQL statement.",
    "SummaryResult_AliasesEntry": "Alias mapping entry in a summarized SQL statement.",
    "SummaryResult_Function": "Function referenced in a summarized SQL statement.",
    "SummaryResult_FilterColumn": "Column used in a filter (``WHERE``) in a summarized SQL statement.",
    # -- table / target --
    "TableFunc": "Table function definition (used by ``XMLTABLE`` and similar, planner node).",
    "TableLikeClause": "``LIKE`` clause in ``CREATE TABLE`` (copies structure from another table).",
    "TableSampleClause": "``TABLESAMPLE`` clause (planner node).",
    "TargetEntry": "Single entry in a query's target list (planner node).",
    # -- TRANSACTION / TRIGGER / TRUNCATE --
    "TransactionStmt": "Transaction control statement (``BEGIN``, ``COMMIT``, ``ROLLBACK``, ``SAVEPOINT``, etc.).",
    "TriggerTransition": "``REFERENCING`` transition table clause in ``CREATE TRIGGER``.",
    "TruncateStmt": "``TRUNCATE`` statement.",
    # -- type cast / type name --
    "TypeCast": "Type cast expression (``expr::type`` or ``CAST(expr AS type)``).",
    "TypeName": "Type name with optional modifiers and array bounds.",
    # -- UNLISTEN / UPDATE --
    "UnlistenStmt": "``UNLISTEN`` statement for notification channels.",
    "UpdateStmt": "``UPDATE`` statement.",
    # -- VACUUM / VAR --
    "VacuumRelation": "Single relation in a ``VACUUM`` or ``ANALYZE`` statement.",
    "VacuumStmt": "``VACUUM`` and/or ``ANALYZE`` statement.",
    "Var": "Variable reference (column of a table, planner node).",
    # -- SET / SHOW / VIEW --
    "VariableSetStmt": "``SET`` configuration variable statement.",
    "VariableShowStmt": "``SHOW`` configuration variable statement.",
    "ViewStmt": "``CREATE VIEW`` statement.",
    # -- WINDOW --
    "WindowClause": "Window specification in a query plan (planner node).",
    "WindowDef": "``WINDOW`` clause or inline window specification.",
    "WindowFunc": "Window function call (planner node).",
    "WindowFuncRunCondition": "Optimization condition for window function execution (planner node).",
    # -- WITH / XML --
    "WithCheckOption": "``WITH CHECK OPTION`` for views and row-level security (planner node).",
    "WithClause": "``WITH`` clause containing common table expressions.",
    "XmlExpr": "XML expression (``XMLCONCAT``, ``XMLELEMENT``, ``XMLFOREST``, etc.).",
    "XmlSerialize": "``XMLSERIALIZE(content/document AS type)`` expression.",
}


def _is_node_oneof(desc: Descriptor) -> bool:
    """Check if a message descriptor is the Node oneof wrapper."""
    return len(desc.oneofs) == 1 and desc.oneofs[0].name == "node"


def _get_non_node_oneofs(desc: Descriptor) -> list[tuple[str, list[FieldDescriptor]]]:
    """Get oneofs that are NOT the Node wrapper (e.g., A_Const.val)."""
    result = []
    for oneof in desc.oneofs:
        if oneof.name != "node":
            result.append((oneof.name, list(oneof.fields)))
    return result


def _safe_name(name: str) -> str:
    """Append underscore to Python keywords to make valid identifiers."""
    if keyword.iskeyword(name):
        return name + "_"
    return name


def _wrapper_name(msg_desc: Descriptor) -> str:
    """Return the wrapper class name, using underscored parent prefix for nested types."""
    if msg_desc.containing_type is not None:
        return f"{msg_desc.containing_type.name}_{msg_desc.name}"
    return msg_desc.name


def _field_python_type(fd: FieldDescriptor) -> str:
    """Return the Python type annotation for a field."""
    if fd.type == _TYPE_MESSAGE:
        if _is_node_oneof(fd.message_type):
            # Node oneof wrapper -> unwrap to AstNode
            if fd.label == _LABEL_REPEATED:
                return "list[AstNode]"
            return "AstNode | None"
        # Concrete message type
        wrapper = _wrapper_name(fd.message_type)
        if fd.label == _LABEL_REPEATED:
            return f"list[{wrapper}]"
        return f"{wrapper} | None"
    # Scalar/enum types
    scalar = _SCALAR_TYPE_MAP.get(fd.type)
    if scalar is None:
        scalar = "int"  # enums and other integer types
    if fd.label == _LABEL_REPEATED:
        return f"list[{scalar}]"
    return scalar


def _pb_attr(name: str) -> str:
    """Return the expression for accessing a protobuf field, using getattr for keywords."""
    if keyword.iskeyword(name):
        return f'getattr(self._pb, "{name}")'
    return f"self._pb.{name}"


def _field_body(fd: FieldDescriptor) -> str:
    """Return the property body for a field."""
    name = fd.name
    attr = _pb_attr(name)
    if fd.type == _TYPE_MESSAGE:
        wrapper = _wrapper_name(fd.message_type)
        if _is_node_oneof(fd.message_type):
            if fd.label == _LABEL_REPEATED:
                return f"return _wrap_list({attr})"
            return f"return _wrap_node_optional({attr})"
        if fd.label == _LABEL_REPEATED:
            return f'return [_REGISTRY["{wrapper}"](item) for item in {attr}]'
        return f'return _REGISTRY["{wrapper}"]({attr}) if self._pb.HasField({name!r}) else None'
    # Scalar or enum
    if fd.label == _LABEL_REPEATED:
        return f"return list({attr})"
    return f"return {attr}"


def _generate_oneof_property(oneof_name: str, oneof_fields: list[FieldDescriptor]) -> str:
    """Generate a property for a non-Node oneof (like A_Const.val)."""
    lines = []
    lines.append("    @property")
    lines.append(f"    def {oneof_name}(self) -> AstNode | int | float | bool | str | None:")
    lines.append(f"        which = self._pb.WhichOneof({oneof_name!r})")
    lines.append("        if which is None:")
    lines.append("            return None")
    lines.append("        inner = getattr(self._pb, which)")
    # If all oneof fields are messages, wrap them
    all_messages = all(f.type == _TYPE_MESSAGE for f in oneof_fields)
    if all_messages:
        lines.append("        return _wrap(inner)")
    else:
        lines.append("        return inner")
    return "\n".join(lines)


def _pb_type_name(desc: Descriptor) -> str:
    """Return the pg_query_pb2 type reference for a descriptor."""
    if desc.containing_type is not None:
        return f"pg_query_pb2.{desc.containing_type.name}.{desc.name}"
    return f"pg_query_pb2.{desc.name}"


def _generate_class(desc: Descriptor) -> str:
    """Generate a wrapper class for a message type."""
    name = _wrapper_name(desc)
    pb_type = _pb_type_name(desc)
    lines = []
    lines.append(f"class {name}(AstNode):")
    docstring = _CLASS_DOCSTRINGS.get(name)
    if docstring:
        lines.append(f'    """{docstring}"""')
        lines.append("")
    lines.append("    __slots__ = ()")
    lines.append(f"    _pb: {pb_type}")

    # Collect fields NOT part of a non-Node oneof
    non_node_oneofs = _get_non_node_oneofs(desc)
    oneof_field_names = set()
    for _, fields in non_node_oneofs:
        for f in fields:
            oneof_field_names.add(f.name)

    # Regular fields (not part of custom oneofs)
    regular_fields = [f for f in desc.fields if f.name not in oneof_field_names]

    # __match_args__: non-location fields
    match_fields = []
    for fd in regular_fields:
        if fd.name not in _SKIP_MATCH_FIELDS:
            match_fields.append(_safe_name(fd.name))
    for oneof_name, _ in non_node_oneofs:
        match_fields.append(oneof_name)
    if match_fields:
        match_str = ", ".join(f'"{f}"' for f in match_fields)
        lines.append(f"    __match_args__ = ({match_str},)")
    else:
        lines.append("    __match_args__ = ()")

    # Regular field properties
    for fd in regular_fields:
        ptype = _field_python_type(fd)
        body = _field_body(fd)
        prop_name = _safe_name(fd.name)
        lines.append("")
        lines.append("    @property")
        lines.append(f"    def {prop_name}(self) -> {ptype}:")
        lines.append(f"        {body}")

    # Oneof properties (like A_Const.val)
    for oneof_name, oneof_fields in non_node_oneofs:
        lines.append("")
        lines.append(_generate_oneof_property(oneof_name, oneof_fields))

    # If no fields at all, add pass
    if not regular_fields and not non_node_oneofs:
        lines.append("    pass")

    return "\n".join(lines)


def _generate_generated(all_descs: list[Descriptor]) -> str:
    """Generate _generated.py with all wrapper classes and _REGISTRY population."""
    parts: list[str] = []

    # Header
    parts.append(
        textwrap.dedent("""\
        # DO NOT EDIT — generated by scripts/generate_nodes.py
        # ruff: noqa: D100,D101,D102,D105,D107,F821,PIE790
        #
        # Typed AST wrapper classes for all protobuf node types.
        # Regenerate with: uv run python scripts/generate_nodes.py

        from __future__ import annotations

        from typing import TYPE_CHECKING

        from postgast.nodes.base import AstNode, _REGISTRY, _wrap, _wrap_list, _wrap_node_optional

        if TYPE_CHECKING:
            import postgast.pg_query_pb2 as pg_query_pb2
    """)
    )

    # Generate all classes
    for desc in all_descs:
        parts.append("")
        parts.append("")
        parts.append(_generate_class(desc))

    # _REGISTRY.update at bottom
    parts.append("")
    parts.append("")
    registry_entries = []
    for desc in all_descs:
        wrapper = _wrapper_name(desc)
        registry_entries.append(f'    "{desc.name}": {wrapper},')
    parts.append("_REGISTRY.update({")
    for entry in registry_entries:
        parts.append(entry)
    parts.append("})")
    parts.append("")

    return "\n".join(parts)


def _generate_init(wrapper_names: list[str]) -> str:
    """Generate __init__.py that re-exports AstNode, wrap, and all wrapper classes."""
    parts: list[str] = []

    parts.append(
        textwrap.dedent("""\
        # DO NOT EDIT — generated by scripts/generate_nodes.py
        # ruff: noqa: D100,D101,D104,F401
        #
        # Re-exports for the nodes package.
        # Regenerate with: uv run python scripts/generate_nodes.py

        from postgast.nodes.base import AstNode, wrap
    """)
    )

    # Single import from _generated (also triggers _REGISTRY.update)
    names_str = ", ".join(sorted(wrapper_names))
    parts.append(f"from postgast.nodes._generated import {names_str}")

    parts.append("")

    # __all__
    all_names = sorted(["AstNode", "wrap", *wrapper_names])
    parts.append("__all__ = [")
    for name in all_names:
        parts.append(f'    "{name}",')
    parts.append("]")
    parts.append("")

    return "\n".join(parts)


def generate() -> dict[str, str]:
    """Generate the nodes package files.

    Returns:
        A dict mapping filename to content (e.g. {"_generated.py": "...", "__init__.py": "..."}).
        Note: base.py is hand-written and not generated.
    """
    descriptor = pg_query_pb2.DESCRIPTOR

    # Collect all message descriptors (including nested types)
    all_descs: list[Descriptor] = []
    for name in sorted(descriptor.message_types_by_name):
        msg_desc = descriptor.message_types_by_name[name]
        if _is_node_oneof(msg_desc):
            continue
        all_descs.append(msg_desc)
        for nested in msg_desc.nested_types:
            all_descs.append(nested)

    wrapper_names = [_wrapper_name(desc) for desc in all_descs]

    files: dict[str, str] = {}
    files["_generated.py"] = _generate_generated(all_descs)
    files["__init__.py"] = _generate_init(wrapper_names)

    return files


def main() -> None:
    files = generate()

    # Remove old single-file nodes.py if it exists
    old_nodes_py = OUTPUT_DIR.parent / "nodes.py"
    if old_nodes_py.is_file():
        old_nodes_py.unlink()
        print(f"Removed old {old_nodes_py}")

    # Create nodes/ directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Clean stale *generated* files from previous generator versions (letter-split _*.py files,
    # old _base.py, etc.).  Only delete files whose first line marks them as generated by this
    # script; hand-written helpers (base.py, future modules) are left untouched.
    generated_marker = "# DO NOT EDIT — generated by scripts/generate_nodes.py"
    expected_generated = set(files.keys())
    for existing in OUTPUT_DIR.iterdir():
        if existing.is_file() and existing.name.endswith(".py") and existing.name not in expected_generated:
            with existing.open(encoding="utf-8") as f:
                first_line = f.readline()
            if first_line.strip() == generated_marker:
                existing.unlink()
                print(f"Removed stale {existing}")

    # Write all files
    for filename, content in files.items():
        path = OUTPUT_DIR / filename
        path.write_text(content)

    # Format with ruff
    import subprocess

    subprocess.run(["ruff", "format", str(OUTPUT_DIR)], check=True)

    # Count classes
    class_count = files["_generated.py"].count("\nclass ")
    print(f"Generated {OUTPUT_DIR}/")
    print(f"  {len(files)} files (_generated.py, __init__.py)")
    print(f"  {class_count} wrapper classes")


if __name__ == "__main__":
    main()
