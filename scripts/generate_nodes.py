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


# ---- Property/field docstrings ---- #
# Maps field name → docstring.  When a field name appears across many wrapper
# classes the same docstring is reused.  Class-specific overrides live in
# ``_CLASS_FIELD_DOCSTRINGS`` keyed by ``(ClassName, field_name)``.

_FIELD_DOCSTRINGS: dict[str, str] = {
    # -- common structural fields --
    "location": "Character offset of this node in the source SQL, or ``-1`` if unknown.",
    "stmt_location": "Character offset of the statement start in the source SQL.",
    "stmt_len": "Length of the statement in characters (``0`` means 'rest of string').",
    "xpr": "Expression type information (planner internal).",
    # -- identifiers / names --
    "name": "Name of the object.",
    "relname": "Relation (table/view) name.",
    "schemaname": "Schema name, or empty string if unqualified.",
    "catalogname": "Catalog (database) name, or empty string if unqualified.",
    "aliasname": "Alias name.",
    "colname": "Column name.",
    "indexname": "Index name.",
    "servername": "Foreign server name.",
    "dbname": "Database name.",
    "rolename": "Role name.",
    "policy_name": "Policy name.",
    "polname": "Policy name.",
    "conname": "Constraint name.",
    "ctename": "CTE (common table expression) name.",
    "funcname": "Function name components.",
    "opername": "Operator name.",
    "extname": "Extension name.",
    "fdwname": "Foreign data wrapper name.",
    "amname": "Access method name.",
    "label": "Statement label (e.g. for savepoints).",
    "comment": "Comment text.",
    "provider": "Security label provider name.",
    "pubname": "Publication name.",
    # -- relations / targets --
    "relation": "Target relation (table or view reference).",
    "relations": "List of target relations.",
    "target_list": "Target list (result columns or assignments).",
    "returning_list": "``RETURNING`` clause target list.",
    # -- clauses --
    "where_clause": "``WHERE`` clause qualification expression.",
    "having_clause": "``HAVING`` clause qualification expression.",
    "from_clause": "``FROM`` clause entries.",
    "sort_clause": "``ORDER BY`` clause entries.",
    "group_clause": "``GROUP BY`` clause entries.",
    "distinct_clause": "``DISTINCT`` clause entries.",
    "locking_clause": "``FOR UPDATE/SHARE`` locking clause.",
    "window_clause": "``WINDOW`` clause entries.",
    "with_clause": "``WITH`` clause containing CTEs.",
    "limit_count": "``LIMIT`` count expression.",
    "limit_offset": "``OFFSET`` expression.",
    "on_conflict_clause": "``ON CONFLICT`` clause.",
    "values_lists": "``VALUES`` lists for ``INSERT`` or ``VALUES`` clause.",
    "partition_clause": "``PARTITION BY`` clause for a window definition.",
    "order_clause": "``ORDER BY`` clause for a window or aggregate.",
    "cte_list": "List of ``WITH`` clause CTE definitions.",
    # -- arguments / expressions --
    "args": "List of argument nodes.",
    "arg": "Argument expression.",
    "lexpr": "Left-hand expression.",
    "rexpr": "Right-hand expression.",
    "expr": "Expression node.",
    "larg": "Left argument (e.g. left side of a set operation).",
    "rarg": "Right argument (e.g. right side of a set operation).",
    "testexpr": "Test expression (the value being tested).",
    "defresult": "Default result expression (``ELSE`` clause).",
    "quals": "Join qualification expression.",
    "qual": "Qualification expression.",
    # -- type info --
    "type_name": "Data type specification.",
    "typmod": "Type modifier (e.g. precision, length), or ``-1`` if none.",
    "type_oid": "OID of the data type.",
    "resulttype": "OID of the result type.",
    "resultcollid": "OID of the result collation.",
    "resulttypmod": "Type modifier for the result, or ``-1``.",
    "collation": "Collation specification.",
    # -- options / flags --
    "options": "List of option definitions (``DefElem`` nodes).",
    "missing_ok": "If true, suppress error when the object doesn't exist.",
    "if_not_exists": "If true, suppress error when the object already exists.",
    "behavior": "Drop behavior (``RESTRICT`` or ``CASCADE``).",
    "concurrent": "If true, use ``CONCURRENTLY`` mode.",
    "replace": "If true, use ``CREATE OR REPLACE`` semantics.",
    "inh": "If true, include inherited/child tables.",
    "kind": "Node subtype or variant kind.",
    "objtype": "Object type identifier.",
    "override": "Override value for generated columns (``DEFAULT`` or ``USER VALUE``).",
    "skip_data": "If true, do not copy data (e.g. ``WITH NO DATA``).",
    "is_grant": "True for ``GRANT``, false for ``REVOKE``.",
    "nowait": "If true, use ``NOWAIT`` option.",
    "deferrable": "If true, the constraint is deferrable.",
    "initdeferred": "If true, the constraint is initially deferred.",
    "is_local": "If true, the constraint is defined locally (not inherited).",
    "is_natural": "If true, this is a ``NATURAL`` join.",
    "lateral": "If true, this is a ``LATERAL`` subquery or function.",
    "recursive": "If true, the ``WITH`` clause uses ``RECURSIVE``.",
    # -- alias / join --
    "alias": "Alias for this range table entry.",
    "jointype": "Join type (``INNER``, ``LEFT``, ``RIGHT``, ``FULL``, ``CROSS``).",
    # -- aggregates (planner) --
    "aggfnoid": "OID of the aggregate function.",
    "aggtype": "OID of the aggregate's result type.",
    "aggcollid": "OID of the aggregate's result collation.",
    "aggstar": "True for ``agg(*)`` (no arguments).",
    "aggvariadic": "True if the aggregate was called with ``VARIADIC``.",
    "aggkind": "Aggregate kind character (normal, ordered-set, or hypothetical).",
    "agglevelsup": "Number of query levels up to find the aggregate's defining query.",
    "aggsplit": "Expected partial-aggregation mode (planner internal).",
    "aggno": "Aggregate number within the query (planner internal).",
    "aggtransno": "Aggregate transition state number (planner internal).",
    "aggdirectargs": "Direct arguments for ordered-set aggregates.",
    "aggargtypes": "OID list of argument types for the aggregate.",
    "aggorder": "``ORDER BY`` clause within the aggregate.",
    "aggdistinct": "``DISTINCT`` entries within the aggregate.",
    "aggfilter": "``FILTER (WHERE …)`` expression for the aggregate.",
    "inputcollid": "OID of the input collation.",
    "inputcollids": "List of input collation OIDs.",
    # -- Var fields (planner) --
    "varno": "Range table index of the relation.",
    "varattno": "Attribute number (column index) within the relation.",
    "vartype": "OID of the variable's data type.",
    "vartypmod": "Type modifier for the variable, or ``-1``.",
    "varcollid": "OID of the variable's collation.",
    "varlevelsup": "Number of query levels up to the defining query.",
    # -- SubLink / SubPlan --
    "sub_link_type": "Type of sub-link (``EXISTS``, ``ANY``, ``ALL``, scalar, etc.).",
    "subselect": "The sub-``SELECT`` query.",
    # -- Param --
    "paramid": "Parameter index or slot number.",
    "paramtype": "OID of the parameter's data type.",
    "paramtypmod": "Type modifier for the parameter, or ``-1``.",
    "paramcollid": "OID of the parameter's collation.",
    "paramkind": "Parameter kind (external, internal, etc.).",
    # -- sort / group --
    "sortby_dir": "Sort direction (``ASC``, ``DESC``, ``USING``, or default).",
    "sortby_nulls": "``NULLS FIRST`` / ``NULLS LAST`` / default.",
    "use_op": "Operator to use for ``ORDER BY … USING`` sorting.",
    # -- scan / parse results --
    "stmts": "List of raw statement nodes.",
    "tokens": "List of scan tokens.",
    "version": "Parse tree version number.",
    # -- INSERT / UPDATE / DELETE --
    "cols": "Target column list (e.g. for ``INSERT``).",
    "select_stmt": "``SELECT`` or ``VALUES`` clause providing rows.",
    # -- CREATE TABLE --
    "table_elts": "List of column definitions and table constraints.",
    "inh_relations": "List of inherited parent tables.",
    "tablespacename": "Tablespace name.",
    "on_commit": "``ON COMMIT`` action for temporary tables.",
    "constraints": "List of constraint definitions.",
    # -- functions / procedures --
    "parameters": "List of function parameter definitions.",
    "return_type": "Return type of the function.",
    "func_options": "List of function option definitions.",
    "sql_body": "SQL function body (parsed statement list).",
    # -- COPY --
    "filename": "Source or destination file name, or ``None`` for stdin/stdout.",
    "is_from": "True for ``COPY FROM``, false for ``COPY TO``.",
    "is_program": "True if *filename* is a shell command (``PROGRAM``).",
    # -- trigger --
    "trigname": "Trigger name.",
    # -- column definition --
    "cooked_default": "Pre-cooked default expression (planner internal).",
    "raw_default": "Raw default expression (before cooking).",
    "identity_type": "Identity column type (``ALWAYS`` or ``BY DEFAULT``), or NUL character if none.",
    "generated": "Generated column kind (``STORED``), or NUL character if not generated.",
    "compression": "Column compression method name.",
    "storage": "Storage strategy name (``PLAIN``, ``EXTENDED``, etc.).",
    "inhcount": "Number of times the column is inherited.",
    "is_not_null": "If true, the column has a ``NOT NULL`` constraint.",
    # -- MERGE --
    "source_relation": "Source relation for a ``MERGE`` statement.",
    "merge_when_clauses": "List of ``WHEN MATCHED/NOT MATCHED`` clauses.",
    "join_condition": "Join condition for the ``MERGE``.",
    # -- JSON --
    "format": "JSON format specification.",
    "encoding": "JSON encoding specification.",
    "output": "JSON output type clause.",
    # -- misc common --
    "stmt": "The wrapped statement node.",
    "query": "The query tree or query string.",
    "object": "Object name or identifier.",
    "indirection": "Indirection chain (field selections and subscripts).",
    "fields": "List of field names in a column reference.",
    "elements": "List of elements.",
    "columns": "List of column specifications.",
    "items": "List of items.",
    "action": "Action specification.",
    "roles": "List of role specifications.",
    "privileges": "List of privilege specifications.",
    "grantees": "List of grantee role specifications.",
    "objects": "List of object identifiers.",
    "definition": "List of definition items.",
    "actions": "List of action clauses.",
    "event": "Event type (``INSERT``, ``UPDATE``, ``DELETE``, ``TRUNCATE``).",
    "condition": "Condition expression.",
    "subname": "Sub-object name.",
    "newname": "New name in a ``RENAME`` operation.",
    "newowner": "New owner role specification.",
    "newschema": "New schema name in a ``SET SCHEMA`` operation.",
    # -- common misc fields --
    "colnames": "List of column name nodes.",
    "collname": "Collation name components.",
    "setstmt": "``SET``/``RESET`` variable sub-statement.",
    "defnames": "Definition name components.",
    "func": "Function call or definition node.",
    "cfgname": "Text search configuration name components.",
    "conninfo": "Connection info string for subscriptions.",
    "publication": "Publication name.",
    "opfamilyname": "Operator family name components.",
    "funcid": "OID of the function.",
    "funccollid": "OID of the function's result collation.",
    "funcresulttype": "OID of the function's result type.",
    "funcretset": "True if the function returns a set.",
    "funcvariadic": "True if the function was called with ``VARIADIC``.",
    "funcformat": "Function display format (explicit, implicit, etc.).",
    "opno": "OID of the operator.",
    "opcollid": "OID of the operator's result collation.",
    "opresulttype": "OID of the operator's result type.",
    "opretset": "True if the operator returns a set.",
    "relpersistence": "Persistence: ``p`` permanent, ``u`` unlogged, ``t`` temporary.",
    "subtype": "Sub-command type.",
    "tgenabled": "Trigger enabled state character.",
    "table": "Table specification.",
    "pubobjects": "Publication object specifications.",
    "role": "Role specification.",
    "database": "Database name.",
    "pubtable": "Publication table specification.",
    "pubobjtype": "Publication object type.",
    "func_name": "Function name components.",
    "sequence": "Sequence relation specification.",
    "defnamespace": "Definition namespace.",
    "stxcomment": "Comment for the statistics object.",
    "stxstattarget": "Statistics target value.",
    "remove": "True for removal operations.",
    "remove_type": "Type of object to remove.",
    "rename_type": "Type of object to rename.",
    "result": "Result expression or value.",
    "node": "Child node.",
    "coerceformat": "Coercion display format.",
    "coercion": "Coercion specification.",
    "row": "Row expression.",
    "row_format": "Row format specification.",
    "def_": "Definition expression.",
}

# Class-specific field docstrings override the generic ones above.
_CLASS_FIELD_DOCSTRINGS: dict[tuple[str, str], str] = {
    ("A_Const", "isnull"): "True if this is a ``NULL`` constant.",
    ("A_Const", "val"): "The constant's value (string, integer, float, or bit-string node).",
    ("A_Expr", "kind"): "Expression kind (``=``, ``<>``, ``AND``, ``OR``, ``LIKE``, etc.).",
    ("A_Expr", "name"): "Operator name components.",
    ("A_Indices", "is_slice"): "True for a slice (``[lo:hi]``), false for a single subscript.",
    ("A_Indices", "lidx"): "Lower bound expression (for slices), or ``None``.",
    ("A_Indices", "uidx"): "Upper bound expression or single subscript expression.",
    ("A_Indirection", "arg"): "Base expression being subscripted or field-selected.",
    ("BoolExpr", "boolop"): "Boolean operator (``AND``, ``OR``, ``NOT``).",
    ("BoolExpr", "args"): "Operand expressions.",
    ("CaseExpr", "arg"): "Implicit equality comparison argument, or ``None`` for searched ``CASE``.",
    ("CaseExpr", "args"): "List of ``WHEN … THEN …`` clauses.",
    ("CaseExpr", "defresult"): "``ELSE`` expression, or ``None`` if no ``ELSE``.",
    ("CaseWhen", "expr"): "``WHEN`` condition expression.",
    ("CaseWhen", "result"): "``THEN`` result expression.",
    ("ColumnRef", "fields"): "Column name components (e.g. ``[schema, table, column]``).",
    ("CommonTableExpr", "ctequery"): "The CTE's query (``SELECT``, ``INSERT``, etc.).",
    ("CommonTableExpr", "ctename"): "Name of the common table expression.",
    ("CommonTableExpr", "aliascolnames"): "Optional column alias list.",
    ("DeleteStmt", "relation"): "Target table to delete from.",
    ("DeleteStmt", "using_clause"): "``USING`` clause entries.",
    ("FuncCall", "funcname"): "Function name components (e.g. ``[schema, func]``).",
    ("FuncCall", "args"): "List of argument expressions.",
    ("FuncCall", "agg_order"): "``ORDER BY`` within an aggregate call.",
    ("FuncCall", "agg_filter"): "``FILTER (WHERE …)`` clause for an aggregate.",
    ("FuncCall", "agg_within_group"): "True for ordered-set (``WITHIN GROUP``) aggregates.",
    ("FuncCall", "agg_star"): "True for ``func(*)``.",
    ("FuncCall", "agg_distinct"): "True for ``func(DISTINCT …)``.",
    ("FuncCall", "over"): "``OVER`` clause (window specification).",
    ("FuncCall", "func_variadic"): "True if last argument uses ``VARIADIC``.",
    ("InsertStmt", "relation"): "Target table to insert into.",
    ("InsertStmt", "cols"): "Target column list, or empty for all columns.",
    ("InsertStmt", "select_stmt"): "``SELECT``, ``VALUES``, or ``DEFAULT VALUES`` source.",
    ("InsertStmt", "on_conflict_clause"): "``ON CONFLICT`` clause, or ``None``.",
    ("JoinExpr", "larg"): "Left-hand relation.",
    ("JoinExpr", "rarg"): "Right-hand relation.",
    ("JoinExpr", "quals"): "``ON`` clause qualification, or ``None``.",
    ("JoinExpr", "using_clause"): "``USING`` clause column list, or ``None``.",
    ("MergeStmt", "relation"): "Target table to merge into.",
    ("RangeVar", "relname"): "Table or view name.",
    ("RangeVar", "schemaname"): "Schema name, or empty if unqualified.",
    ("RangeVar", "catalogname"): "Catalog name, or empty if unqualified.",
    ("RangeVar", "inh"): "If true, include child tables (inheritance).",
    ("RangeVar", "relpersistence"): "Persistence: ``p`` permanent, ``u`` unlogged, ``t`` temporary.",
    ("RangeVar", "alias"): "Table alias, or ``None``.",
    ("RawStmt", "stmt"): "The parsed statement node.",
    ("RawStmt", "stmt_location"): "Byte offset of the statement start in the source SQL.",
    ("RawStmt", "stmt_len"): "Statement length in bytes (``0`` means rest of string).",
    ("ResTarget", "name"): "Column name for ``INSERT`` target, alias for ``SELECT``, or ``None``.",
    ("ResTarget", "val"): "Value expression.",
    ("ResTarget", "indirection"): "Subscripts/field selections on the target column.",
    ("SelectStmt", "target_list"): "``SELECT`` target list (result columns).",
    ("SelectStmt", "from_clause"): "``FROM`` clause entries.",
    ("SelectStmt", "where_clause"): "``WHERE`` clause, or ``None``.",
    ("SelectStmt", "group_clause"): "``GROUP BY`` clause entries.",
    ("SelectStmt", "having_clause"): "``HAVING`` clause, or ``None``.",
    ("SelectStmt", "sort_clause"): "``ORDER BY`` clause entries.",
    ("SelectStmt", "larg"): "Left input for set operations (``UNION``, etc.).",
    ("SelectStmt", "rarg"): "Right input for set operations.",
    ("SelectStmt", "op"): "Set operation type (``UNION``, ``INTERSECT``, ``EXCEPT``, or ``NONE``).",
    ("SelectStmt", "all"): "True for ``ALL`` (no duplicate elimination in set ops).",
    ("SortBy", "node"): "Expression to sort by.",
    ("SortBy", "sortby_dir"): "Sort direction (``ASC``, ``DESC``, ``USING``, or default).",
    ("SortBy", "sortby_nulls"): "``NULLS FIRST`` / ``NULLS LAST`` / default.",
    ("SortBy", "use_op"): "Operator for ``ORDER BY … USING``.",
    ("SubLink", "sub_link_type"): "Subquery type (``EXISTS``, ``ANY``, ``ALL``, ``EXPR``, etc.).",
    ("SubLink", "testexpr"): "Left-hand test expression (for ``ANY``/``ALL``), or ``None``.",
    ("SubLink", "subselect"): "The sub-``SELECT`` query.",
    ("TypeCast", "arg"): "Expression to cast.",
    ("TypeCast", "type_name"): "Target data type.",
    ("TypeName", "names"): "Type name components (e.g. ``[pg_catalog, int4]``).",
    ("TypeName", "typmods"): "Type modifiers (e.g. precision, scale).",
    ("TypeName", "array_bounds"): "Array dimension bounds (``-1`` for unspecified).",
    ("TypeName", "setof"): "True if ``SETOF`` type.",
    ("TypeName", "pct_type"): "True if ``%TYPE`` reference.",
    ("UpdateStmt", "relation"): "Target table to update.",
    ("UpdateStmt", "target_list"): "``SET`` clause assignments.",
    ("UpdateStmt", "from_clause"): "``FROM`` clause entries.",
    ("WindowDef", "name"): "Window name (for ``WINDOW`` clause), or empty for inline.",
    ("WindowDef", "refname"): "Name of a referenced existing window definition.",
    ("WindowDef", "partition_clause"): "``PARTITION BY`` expressions.",
    ("WindowDef", "order_clause"): "``ORDER BY`` entries.",
    ("WindowDef", "frame_options"): "Frame option bit flags.",
    ("WindowDef", "start_offset"): "Frame start offset expression.",
    ("WindowDef", "end_offset"): "Frame end offset expression.",
    ("Constraint", "contype"): "Constraint type (``CHECK``, ``UNIQUE``, ``PRIMARY KEY``, ``FOREIGN KEY``, etc.).",
    ("Constraint", "conname"): "Constraint name, or empty for unnamed.",
    ("Constraint", "raw_expr"): "``CHECK`` expression (raw parse tree).",
    ("Constraint", "keys"): "List of key column names.",
    ("Constraint", "fk_attrs"): "Foreign key column names in the referencing table.",
    ("Constraint", "pk_attrs"): "Referenced column names in the target table.",
    ("Constraint", "pktable"): "Referenced table for a foreign key.",
    ("ColumnDef", "colname"): "Column name.",
    ("ColumnDef", "type_name"): "Column data type.",
    ("ColumnDef", "constraints"): "Column constraints (``NOT NULL``, ``CHECK``, etc.).",
    ("ColumnDef", "raw_default"): "Default value expression (raw parse tree).",
    ("DefElem", "defname"): "Option name.",
    ("DefElem", "arg"): "Option value expression, or ``None`` for a bare keyword.",
    ("DefElem", "defaction"): "Action (``SET``, ``ADD``, ``DROP``).",
    ("DefElem", "defnamespace"): "Option namespace (rarely used).",
    ("IndexElem", "name"): "Column name, or ``None`` for an expression index.",
    ("IndexElem", "expr"): "Index expression, or ``None`` for a simple column.",
    ("IndexElem", "indexcolname"): "Column name for index references.",
    ("IndexElem", "opclass"): "Operator class names.",
    ("IndexElem", "ordering"): "Sort ordering (``ASC`` or ``DESC``).",
    ("IndexElem", "nulls_ordering"): "``NULLS FIRST`` or ``NULLS LAST``.",
    ("CreateStmt", "relation"): "Table name and schema.",
    ("CreateStmt", "table_elts"): "Column definitions and table constraints.",
    ("CreateStmt", "inh_relations"): "``INHERITS`` parent table list.",
    ("CreateStmt", "partspec"): "``PARTITION BY`` specification, or ``None``.",
    ("CreateStmt", "partbound"): "Partition bound, or ``None``.",
    ("CreateStmt", "tablespacename"): "Tablespace name, or empty for default.",
    ("CreateStmt", "on_commit"): "``ON COMMIT`` action for temporary tables.",
    ("IndexStmt", "idxname"): "Index name.",
    ("IndexStmt", "relation"): "Table to create the index on.",
    ("IndexStmt", "access_method"): "Index access method (e.g. ``btree``, ``hash``).",
    ("IndexStmt", "index_params"): "List of index column/expression elements.",
    ("IndexStmt", "unique"): "True for a ``UNIQUE`` index.",
    ("IndexStmt", "concurrent"): "True for ``CREATE INDEX CONCURRENTLY``.",
    ("IndexStmt", "where_clause"): "Partial index predicate, or ``None``.",
    ("ParseResult", "stmts"): "List of raw statement wrappers from the parsed SQL.",
    ("ParseResult", "version"): "Parse tree version number.",
    ("ScanResult", "tokens"): "List of scanner tokens.",
    ("ScanResult", "version"): "Scanner version number.",
    ("ScanToken", "start"): "Byte offset of the token start.",
    ("ScanToken", "end"): "Byte offset past the token end.",
    ("ScanToken", "token"): "Token kind identifier.",
    ("ScanToken", "keyword_kind"): "Keyword classification (reserved, unreserved, etc.).",
}


def _humanize_field(field_name: str) -> str:
    """Convert a snake_case field name into a brief human-readable description."""
    # Handle is_/has_ boolean prefixes
    if field_name.startswith("is_"):
        rest = field_name[3:].replace("_", " ")
        return f"Whether this is {rest}."
    if field_name.startswith("has_"):
        rest = field_name[4:].replace("_", " ")
        return f"Whether this has {rest}."
    # Generic: replace underscores, capitalize first letter
    words = field_name.replace("_", " ")
    return words[0].upper() + words[1:] + "."


def _field_docstring(class_name: str, field_name: str, python_type: str) -> str:
    """Return the docstring for a generated property."""
    # 1. Class-specific override
    key = (class_name, field_name)
    if key in _CLASS_FIELD_DOCSTRINGS:
        return _CLASS_FIELD_DOCSTRINGS[key]
    # 2. Generic field name
    if field_name in _FIELD_DOCSTRINGS:
        return _FIELD_DOCSTRINGS[field_name]
    # 3. Auto-generated fallback
    return _humanize_field(field_name)


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


def _generate_oneof_property(class_name: str, oneof_name: str, oneof_fields: list[FieldDescriptor]) -> str:
    """Generate a property for a non-Node oneof (like A_Const.val)."""
    ptype = "AstNode | int | float | bool | str | None"
    doc = _field_docstring(class_name, oneof_name, ptype)
    lines = []
    lines.append("    @property")
    lines.append(f"    def {oneof_name}(self) -> {ptype}:")
    lines.append(f'        """{doc}"""')
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
        doc = _field_docstring(name, fd.name, ptype)
        lines.append("")
        lines.append("    @property")
        lines.append(f"    def {prop_name}(self) -> {ptype}:")
        lines.append(f'        """{doc}"""')
        lines.append(f"        {body}")

    # Oneof properties (like A_Const.val)
    for oneof_name, oneof_fields in non_node_oneofs:
        lines.append("")
        lines.append(_generate_oneof_property(name, oneof_name, oneof_fields))

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
        # ruff: noqa: D100,D101,D105,D107,F821,PIE790
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
