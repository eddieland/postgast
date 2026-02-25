"""Migration Static Analysis — framework and built-in checks for dangerous migration patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

import marimo

if TYPE_CHECKING:
    import types
    from collections.abc import Callable

    from postgast import ParseResult

__generated_with = "0.19.11"
app = marimo.App()


# ── Section 1: Framework Core ────────────────────────────────────────────


@app.cell
def _(mo: types.ModuleType):
    mo.md("""
    # Migration Static Analysis

    A framework-style migration linter built on **postgast**.  It parses each SQL
    statement, walks the protobuf AST, and flags dangerous patterns that can cause
    downtime during PostgreSQL schema migrations.

    **Sections:**

    1. **Framework Core** — `Severity`, `Violation`, `Check` protocol, `CheckRunner`
    2. **Built-in Checks** — 10 checks for the most dangerous migration patterns
    3. **Interactive Demos** — good vs bad migrations, configuration, custom checks

    **How to use this notebook:**

    - `marimo run recipes/migration_checks.py` — read-only app mode
    - `marimo edit recipes/migration_checks.py` — interactive editing mode
    """)
    return


@app.cell
def _():
    import marimo as mo

    from postgast import deparse, find_nodes, parse, split, walk
    from postgast import pg_query_pb2 as pb
    from postgast.walk import _unwrap_node  # pyright: ignore[reportPrivateUsage]

    return _unwrap_node, deparse, find_nodes, mo, parse, pb, split, walk


@app.cell
def _(pb: types.ModuleType):
    import dataclasses
    import enum
    from typing import Protocol, runtime_checkable

    class Severity(enum.Enum):
        error = "error"
        warning = "warning"
        info = "info"

    @dataclasses.dataclass(frozen=True, slots=True)
    class Violation:
        check_id: str
        severity: Severity
        message: str
        hint: str
        statement_sql: str | None = None
        table: str | None = None

    @runtime_checkable
    class Check(Protocol):
        @property
        def id(self) -> str: ...
        @property
        def description(self) -> str: ...
        @property
        def severity(self) -> Severity: ...
        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]: ...  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]

    return Check, Severity, Violation, dataclasses, enum, runtime_checkable


@app.cell
def _(
    Check: type,
    Severity: type,
    Violation: type,
    mo: types.ModuleType,
    parse: Callable[[str], ParseResult],
    split: Callable[[str], list[str]],
):
    class CheckRunner:
        """Runs registered checks against SQL statements."""

        def __init__(self) -> None:
            self._checks: list[Check] = []  # pyright: ignore[reportMissingTypeArgument]
            self._overrides: dict[str, dict[str, object]] = {}

        def register(self, check: Check) -> None:  # pyright: ignore[reportMissingTypeArgument]
            self._checks.append(check)

        def configure(self, check_id: str, *, enabled: bool | None = None, severity: Severity | None = None) -> None:  # pyright: ignore[reportGeneralTypeIssues]
            self._overrides.setdefault(check_id, {})
            if enabled is not None:
                self._overrides[check_id]["enabled"] = enabled
            if severity is not None:
                self._overrides[check_id]["severity"] = severity

        def _is_enabled(self, check: Check) -> bool:  # pyright: ignore[reportMissingTypeArgument]
            ovr = self._overrides.get(check.id, {})
            return ovr.get("enabled", True)  # pyright: ignore[reportReturnType]

        def _effective_severity(self, check: Check) -> Severity:  # pyright: ignore[reportMissingTypeArgument, reportGeneralTypeIssues]
            ovr = self._overrides.get(check.id, {})
            return ovr.get("severity", check.severity)  # pyright: ignore[reportReturnType]

        def run(self, sql: str) -> list[Violation]:  # pyright: ignore[reportGeneralTypeIssues]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            statements = split(sql)
            for stmt_sql in statements:
                tree = parse(stmt_sql)
                if not tree.stmts:
                    continue
                stmt_node = tree.stmts[0].stmt
                for check in self._checks:
                    if not self._is_enabled(check):
                        continue
                    eff_severity = self._effective_severity(check)
                    for v in check.check(stmt_node, stmt_sql):
                        violations.append(
                            Violation(  # pyright: ignore[reportGeneralTypeIssues]
                                check_id=v.check_id,
                                severity=eff_severity,
                                message=v.message,
                                hint=v.hint,
                                statement_sql=v.statement_sql,
                                table=v.table,
                            )
                        )
            return violations

        def run_file(self, path: str) -> list[Violation]:  # pyright: ignore[reportGeneralTypeIssues]
            with open(path) as f:
                return self.run(f.read())

    def _format_violations(violations: list[Violation]) -> str:  # pyright: ignore[reportGeneralTypeIssues]
        """Format violations as a markdown table for display."""
        if not violations:
            return "**No violations found.**"
        rows: list[str] = []
        for v in violations:
            sev_icon = {"error": "!!!", "warning": "!!", "info": "i"}[v.severity.value]
            sql_preview = (v.statement_sql or "")[:60]
            if v.statement_sql and len(v.statement_sql) > 60:
                sql_preview += "..."
            rows.append(f"| **{sev_icon}** | `{v.check_id}` | {v.message} | `{sql_preview}` |")
        header = "| Sev | Check | Message | SQL |\n|-----|-------|---------|-----|\n"
        return header + "\n".join(rows)

    mo.md("""
    ## Framework Core

    - **`Severity`** — `error`, `warning`, `info`
    - **`Violation`** — a single finding with check ID, message, hint, and SQL context
    - **`Check`** — protocol for pluggable checks: `id`, `description`, `severity`, `check(stmt_node, raw_sql)`
    - **`CheckRunner`** — split SQL, parse each statement, run all enabled checks
    - **`_format_violations`** — display helper for marimo output
    """)
    return CheckRunner, _format_violations


# ── Section 2: Built-in Checks ───────────────────────────────────────────


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class SetNotNullCheck:
        """Detects ALTER TABLE ... ALTER COLUMN ... SET NOT NULL."""

        id = "set-not-null"
        description = "SET NOT NULL requires a full table scan and ACCESS EXCLUSIVE lock"
        severity = Severity.error  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype == pb.AT_SetNotNull:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"SET NOT NULL on column `{cmd.name}`",
                            hint=(
                                "Add a CHECK constraint with NOT VALID first, then VALIDATE CONSTRAINT "
                                "in a separate transaction to avoid a full table scan under an ACCESS EXCLUSIVE lock."
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `set-not-null`

    Detects `ALTER TABLE ... ALTER COLUMN ... SET NOT NULL`.
    This acquires an **ACCESS EXCLUSIVE** lock and performs a full table scan
    to verify no NULLs exist.
    """)
    return (SetNotNullCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    find_nodes: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class AddColumnNotNullNoDefaultCheck:
        """Detects ADD COLUMN ... NOT NULL without a DEFAULT."""

        id = "add-column-not-null-no-default"
        description = "ADD COLUMN NOT NULL without DEFAULT fails if the table has rows"
        severity = Severity.error  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype != pb.AT_AddColumn:
                    continue
                if not cmd.HasField("def"):
                    continue
                col_def = _unwrap_node(getattr(cmd, "def"))
                if not isinstance(col_def, pb.ColumnDef):
                    continue
                has_not_null = col_def.is_not_null
                if not has_not_null:
                    for constraint_node in col_def.constraints:
                        c = _unwrap_node(constraint_node)
                        if isinstance(c, pb.Constraint) and c.contype == pb.CONSTR_NOTNULL:
                            has_not_null = True
                            break
                has_default = col_def.HasField("raw_default")
                if has_not_null and not has_default:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"ADD COLUMN `{col_def.colname}` is NOT NULL without a DEFAULT",
                            hint=(
                                "Add the column as nullable first, backfill data, then add a NOT NULL "
                                "constraint with NOT VALID."
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `add-column-not-null-no-default`

    Detects `ALTER TABLE ... ADD COLUMN ... NOT NULL` without a `DEFAULT` clause.
    On PostgreSQL < 11 this rewrites the entire table; on any version it fails
    outright if rows already exist.
    """)
    return (AddColumnNotNullNoDefaultCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class CreateIndexNotConcurrentCheck:
        """Detects CREATE INDEX without CONCURRENTLY."""

        id = "create-index-not-concurrent"
        description = "CREATE INDEX without CONCURRENTLY holds a SHARE lock blocking all writes"
        severity = Severity.error  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "index_stmt":
                return violations
            index = getattr(stmt_node, which)
            if not index.concurrent:
                table_name = index.relation.relname if index.HasField("relation") else None
                violations.append(
                    Violation(  # pyright: ignore[reportGeneralTypeIssues]
                        check_id=self.id,
                        severity=self.severity,
                        message=f"CREATE INDEX `{index.idxname}` is not CONCURRENTLY",
                        hint="Use CREATE INDEX CONCURRENTLY to avoid blocking writes during index creation.",
                        statement_sql=raw_sql.strip(),
                        table=table_name,
                    )
                )
            return violations

    mo.md("""
    ### Check: `create-index-not-concurrent`

    Detects `CREATE INDEX` without the `CONCURRENTLY` keyword.
    A non-concurrent index build holds a **SHARE** lock on the table,
    blocking all writes for the duration of the build.
    """)
    return (CreateIndexNotConcurrentCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class AddForeignKeyNoNotValidCheck:
        """Detects ADD CONSTRAINT ... FOREIGN KEY without NOT VALID."""

        id = "add-fk-no-not-valid"
        description = "Adding a FK without NOT VALID acquires ACCESS EXCLUSIVE on both tables"
        severity = Severity.error  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype != pb.AT_AddConstraint:
                    continue
                if not cmd.HasField("def"):
                    continue
                constraint = _unwrap_node(getattr(cmd, "def"))
                if not isinstance(constraint, pb.Constraint):
                    continue
                if constraint.contype != pb.CONSTR_FOREIGN:
                    continue
                if not constraint.skip_validation:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"FOREIGN KEY constraint `{constraint.conname}` added without NOT VALID",
                            hint=(
                                "Add the FK with NOT VALID first, then run ALTER TABLE ... VALIDATE CONSTRAINT "
                                "in a separate transaction. This avoids an ACCESS EXCLUSIVE lock on both tables."
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `add-fk-no-not-valid`

    Detects `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` without `NOT VALID`.
    This acquires an **ACCESS EXCLUSIVE** lock on *both* tables to verify
    referential integrity.
    """)
    return (AddForeignKeyNoNotValidCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class AddCheckNoNotValidCheck:
        """Detects ADD CONSTRAINT ... CHECK without NOT VALID."""

        id = "add-check-no-not-valid"
        description = "Adding a CHECK without NOT VALID causes a full table scan under lock"
        severity = Severity.warning  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype != pb.AT_AddConstraint:
                    continue
                if not cmd.HasField("def"):
                    continue
                constraint = _unwrap_node(getattr(cmd, "def"))
                if not isinstance(constraint, pb.Constraint):
                    continue
                if constraint.contype != pb.CONSTR_CHECK:
                    continue
                if not constraint.skip_validation:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"CHECK constraint `{constraint.conname}` added without NOT VALID",
                            hint=(
                                "Add the CHECK with NOT VALID first, then VALIDATE CONSTRAINT in a "
                                "separate transaction to avoid a full table scan under an ACCESS EXCLUSIVE lock."
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `add-check-no-not-valid`

    Detects `ALTER TABLE ... ADD CONSTRAINT ... CHECK (...)` without `NOT VALID`.
    This causes a full table scan under an **ACCESS EXCLUSIVE** lock to verify
    the constraint holds for all existing rows.
    """)
    return (AddCheckNoNotValidCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class AlterColumnTypeCheck:
        """Detects ALTER TABLE ... ALTER COLUMN ... TYPE."""

        id = "alter-column-type"
        description = "Changing column type rewrites the entire table under ACCESS EXCLUSIVE lock"
        severity = Severity.error  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype == pb.AT_AlterColumnType:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"ALTER COLUMN `{cmd.name}` TYPE causes a full table rewrite",
                            hint=(
                                "Consider adding a new column with the target type, backfilling data, "
                                "then swapping columns. Some type changes (e.g., varchar(N) to varchar(M) where M > N) "
                                "are safe and don't rewrite."
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `alter-column-type`

    Detects `ALTER TABLE ... ALTER COLUMN ... TYPE`.  Most type changes cause a
    full table rewrite under an **ACCESS EXCLUSIVE** lock.
    """)
    return (AlterColumnTypeCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class AddUniqueConstraintCheck:
        """Detects ALTER TABLE ... ADD UNIQUE (not via index)."""

        id = "add-unique-constraint"
        description = "Adding a UNIQUE constraint builds an index under ACCESS EXCLUSIVE lock"
        severity = Severity.warning  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype != pb.AT_AddConstraint:
                    continue
                if not cmd.HasField("def"):
                    continue
                constraint = _unwrap_node(getattr(cmd, "def"))
                if not isinstance(constraint, pb.Constraint):
                    continue
                if constraint.contype == pb.CONSTR_UNIQUE:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"UNIQUE constraint `{constraint.conname}` builds an index under lock",
                            hint=(
                                "Create a UNIQUE INDEX CONCURRENTLY first, then add the constraint using "
                                "the pre-built index: ALTER TABLE ... ADD CONSTRAINT ... UNIQUE USING INDEX ...;"
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `add-unique-constraint`

    Detects `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE`.  This builds the
    underlying index while holding an **ACCESS EXCLUSIVE** lock, blocking all
    reads and writes.
    """)
    return (AddUniqueConstraintCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class AddExclusionConstraintCheck:
        """Detects ALTER TABLE ... ADD CONSTRAINT ... EXCLUDE."""

        id = "add-exclusion-constraint"
        description = "Adding an EXCLUSION constraint holds ACCESS EXCLUSIVE lock during index build"
        severity = Severity.warning  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype != pb.AT_AddConstraint:
                    continue
                if not cmd.HasField("def"):
                    continue
                constraint = _unwrap_node(getattr(cmd, "def"))
                if not isinstance(constraint, pb.Constraint):
                    continue
                if constraint.contype == pb.CONSTR_EXCLUSION:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"EXCLUSION constraint `{constraint.conname}` holds ACCESS EXCLUSIVE lock",
                            hint=(
                                "Exclusion constraints cannot be added concurrently. Consider adding them "
                                "during a maintenance window or on a low-traffic replica first."
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `add-exclusion-constraint`

    Detects `ALTER TABLE ... ADD CONSTRAINT ... EXCLUDE (...)`.  Exclusion
    constraints require building a GiST index under **ACCESS EXCLUSIVE** lock.
    """)
    return (AddExclusionConstraintCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
    walk: Callable[..., object],
):
    _VOLATILE_FUNCTIONS = frozenset({
        "now",
        "clock_timestamp",
        "random",
        "uuid_generate_v4",
        "gen_random_uuid",
        "statement_timestamp",
        "transaction_timestamp",
        "timeofday",
    })

    def _contains_volatile_call(node: object) -> str | None:  # pyright: ignore[reportUnknownParameterType]
        """Return the volatile function name if found in the expression tree, else None."""
        for _field, child in walk(node):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            if type(child).__name__ == "FuncCall":
                for name_node in child.funcname:  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
                    inner = _unwrap_node(name_node)
                    if type(inner).__name__ == "String" and inner.sval in _VOLATILE_FUNCTIONS:  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
                        return inner.sval  # pyright: ignore[reportUnknownMemberType, reportReturnType, reportAttributeAccessIssue]
        return None

    class AddColumnVolatileDefaultCheck:
        """Detects ADD COLUMN ... DEFAULT <volatile_function()>."""

        id = "add-column-volatile-default"
        description = "ADD COLUMN with a volatile DEFAULT causes a full table rewrite even on PG 11+"
        severity = Severity.warning  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype != pb.AT_AddColumn:
                    continue
                if not cmd.HasField("def"):
                    continue
                col_def = _unwrap_node(getattr(cmd, "def"))
                if not isinstance(col_def, pb.ColumnDef):
                    continue
                if not col_def.HasField("raw_default"):
                    continue
                volatile_fn = _contains_volatile_call(col_def.raw_default)
                if volatile_fn:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"ADD COLUMN `{col_def.colname}` has volatile DEFAULT `{volatile_fn}()`",
                            hint=(
                                "Add the column without a default, then backfill with UPDATE in batches, "
                                "then ALTER COLUMN SET DEFAULT. Volatile defaults force a table rewrite."
                            ),
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    mo.md("""
    ### Check: `add-column-volatile-default`

    Detects `ALTER TABLE ... ADD COLUMN ... DEFAULT now()` (or other volatile
    functions).  Even on PostgreSQL 11+ where immutable defaults are cheap,
    volatile defaults still cause a **full table rewrite**.

    Tracked volatile functions: `now()`, `clock_timestamp()`, `random()`,
    `uuid_generate_v4()`, `gen_random_uuid()`, `statement_timestamp()`,
    `transaction_timestamp()`, `timeofday()`.
    """)
    return (AddColumnVolatileDefaultCheck,)


@app.cell
def _(
    Severity: type,
    Violation: type,
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class DropIndexNotConcurrentCheck:
        """Detects DROP INDEX without CONCURRENTLY."""

        id = "drop-index-not-concurrent"
        description = "DROP INDEX without CONCURRENTLY blocks writes during the drop"
        severity = Severity.warning  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "drop_stmt":
                return violations
            drop = getattr(stmt_node, which)
            if drop.remove_type != pb.OBJECT_INDEX:
                return violations
            if not drop.concurrent:
                violations.append(
                    Violation(  # pyright: ignore[reportGeneralTypeIssues]
                        check_id=self.id,
                        severity=self.severity,
                        message="DROP INDEX without CONCURRENTLY blocks writes",
                        hint="Use DROP INDEX CONCURRENTLY to avoid blocking writes during index removal.",
                        statement_sql=raw_sql.strip(),
                        table=None,
                    )
                )
            return violations

    mo.md("""
    ### Check: `drop-index-not-concurrent`

    Detects `DROP INDEX` without the `CONCURRENTLY` keyword.  A non-concurrent
    drop acquires an **ACCESS EXCLUSIVE** lock on the table.
    """)
    return (DropIndexNotConcurrentCheck,)


# ── Section 3: Interactive Demos ─────────────────────────────────────────


@app.cell
def _(
    AddCheckNoNotValidCheck: type,
    AddColumnNotNullNoDefaultCheck: type,
    AddColumnVolatileDefaultCheck: type,
    AddExclusionConstraintCheck: type,
    AddForeignKeyNoNotValidCheck: type,
    AddUniqueConstraintCheck: type,
    AlterColumnTypeCheck: type,
    CheckRunner: type,
    CreateIndexNotConcurrentCheck: type,
    DropIndexNotConcurrentCheck: type,
    SetNotNullCheck: type,
):
    def _make_runner() -> CheckRunner:  # pyright: ignore[reportGeneralTypeIssues]
        """Create a CheckRunner with all built-in checks registered."""
        runner = CheckRunner()  # pyright: ignore[reportGeneralTypeIssues]
        for check_cls in [
            SetNotNullCheck,
            AddColumnNotNullNoDefaultCheck,
            CreateIndexNotConcurrentCheck,
            AddForeignKeyNoNotValidCheck,
            AddCheckNoNotValidCheck,
            AlterColumnTypeCheck,
            AddUniqueConstraintCheck,
            AddExclusionConstraintCheck,
            AddColumnVolatileDefaultCheck,
            DropIndexNotConcurrentCheck,
        ]:
            runner.register(check_cls())
        return runner

    return (_make_runner,)


@app.cell
def _(
    _format_violations: Callable[..., str],
    _make_runner: Callable[..., object],
    mo: types.ModuleType,
):
    _bad_sql = """\
ALTER TABLE users ADD COLUMN email text NOT NULL;
CREATE INDEX idx_users_email ON users (email);
ALTER TABLE orders ADD CONSTRAINT orders_user_fk FOREIGN KEY (user_id) REFERENCES users (id);
ALTER TABLE orders ALTER COLUMN total TYPE numeric(12, 2);
"""

    _good_sql = """\
ALTER TABLE users ADD COLUMN email text;
UPDATE users SET email = 'unknown@example.com' WHERE email IS NULL;
ALTER TABLE users ADD CONSTRAINT users_email_not_null CHECK (email IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_email_not_null;
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);
ALTER TABLE orders ADD CONSTRAINT orders_user_fk FOREIGN KEY (user_id) REFERENCES users (id) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_user_fk;
"""

    _runner = _make_runner()

    _bad_violations = _runner.run(_bad_sql)
    _good_violations = _runner.run(_good_sql)

    mo.md(
        f"""
        ## Demo 1: Good vs Bad Migration

        **Unsafe migration ({len(_bad_violations)} violations):**

        ```sql
{_bad_sql}        ```

{_format_violations(_bad_violations)}

        ---

        **Safe equivalent ({len(_good_violations)} violations):**

        ```sql
{_good_sql}        ```

{_format_violations(_good_violations)}
        """
    )
    return


@app.cell
def _(
    _format_violations: Callable[..., str],
    _make_runner: Callable[..., object],
    mo: types.ModuleType,
):
    _migration_sql = """\
-- Step 1: Add new columns (safe with defaults)
ALTER TABLE products ADD COLUMN sku text;
ALTER TABLE products ADD COLUMN created_at timestamptz DEFAULT now();

-- Step 2: Create indexes
CREATE INDEX idx_products_sku ON products (sku);
CREATE INDEX CONCURRENTLY idx_products_created ON products (created_at);

-- Step 3: Add constraints
ALTER TABLE products ADD CONSTRAINT products_sku_unique UNIQUE (sku);
ALTER TABLE products ADD CONSTRAINT products_category_fk FOREIGN KEY (category_id) REFERENCES categories (id) NOT VALID;
ALTER TABLE products VALIDATE CONSTRAINT products_category_fk;

-- Step 4: Modify column type
ALTER TABLE products ALTER COLUMN price TYPE numeric(10, 2);

-- Step 5: Add NOT NULL
ALTER TABLE products ALTER COLUMN sku SET NOT NULL;
"""

    _runner = _make_runner()
    _violations = _runner.run(_migration_sql)

    _violation_details = "\n".join(
        f"- **`{v.check_id}`** ({v.severity.value}): {v.message}\n  > *Hint: {v.hint}*" for v in _violations
    )

    mo.md(
        f"""
        ## Demo 2: Multi-Statement Migration Analysis

        A realistic migration with a mix of safe and unsafe statements.

        ```sql
{_migration_sql}        ```

        **{len(_violations)} violations found:**

{_violation_details}
        """
    )
    return


@app.cell
def _(
    CheckRunner: type,
    Severity: type,
    _format_violations: Callable[..., str],
    _make_runner: Callable[..., object],
    mo: types.ModuleType,
):
    _sql = """\
CREATE INDEX idx_orders_date ON orders (created_at);
ALTER TABLE orders ALTER COLUMN amount TYPE bigint;
ALTER TABLE orders ADD CONSTRAINT orders_user_fk FOREIGN KEY (user_id) REFERENCES users (id);
"""

    # Default behavior
    _runner_default = _make_runner()
    _v_default = _runner_default.run(_sql)

    # Disable the index check
    _runner_custom = _make_runner()
    _runner_custom.configure("create-index-not-concurrent", enabled=False)
    _runner_custom.configure("add-fk-no-not-valid", severity=Severity.info)  # pyright: ignore[reportGeneralTypeIssues]
    _v_custom = _runner_custom.run(_sql)

    mo.md(
        f"""
        ## Demo 3: Configuration

        The runner supports per-check overrides via `configure(check_id, *, enabled, severity)`.

        **Default configuration ({len(_v_default)} violations):**

{_format_violations(_v_default)}

        **Custom configuration ({len(_v_custom)} violations):**

        - Disabled `create-index-not-concurrent`
        - Downgraded `add-fk-no-not-valid` severity to `info`

{_format_violations(_v_custom)}
        """
    )
    return


@app.cell
def _(
    Severity: type,
    Violation: type,
    _format_violations: Callable[..., str],
    _make_runner: Callable[..., object],
    _unwrap_node: Callable[..., object],
    mo: types.ModuleType,
    pb: types.ModuleType,
):
    class DropColumnCheck:
        """Custom check: warn on DROP COLUMN."""

        id = "drop-column"
        description = "DROP COLUMN acquires ACCESS EXCLUSIVE lock"
        severity = Severity.info  # pyright: ignore[reportGeneralTypeIssues]

        def check(self, stmt_node: pb.Node, raw_sql: str) -> list[Violation]:  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            violations: list[Violation] = []  # pyright: ignore[reportGeneralTypeIssues]
            which = stmt_node.WhichOneof("node")
            if which != "alter_table_stmt":
                return violations
            alter = getattr(stmt_node, which)
            table_name = alter.relation.relname if alter.HasField("relation") else None
            for cmd_node in alter.cmds:
                cmd = _unwrap_node(cmd_node)
                if cmd.subtype == pb.AT_DropColumn:
                    violations.append(
                        Violation(  # pyright: ignore[reportGeneralTypeIssues]
                            check_id=self.id,
                            severity=self.severity,
                            message=f"DROP COLUMN `{cmd.name}`",
                            hint="Dropping columns is fast but irreversible. Ensure application code no longer references this column.",
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        )
                    )
            return violations

    _sql = """\
ALTER TABLE users DROP COLUMN legacy_role;
ALTER TABLE users ALTER COLUMN name SET NOT NULL;
"""

    _runner = _make_runner()
    _runner.register(DropColumnCheck())
    _violations = _runner.run(_sql)

    mo.md(
        f"""
        ## Demo 4: Custom Check

        Writing a custom check is straightforward — implement the `Check` protocol
        and register it with the runner.

        ```python
        class DropColumnCheck:
            id = "drop-column"
            description = "DROP COLUMN acquires ACCESS EXCLUSIVE lock"
            severity = Severity.info

            def check(self, stmt_node, raw_sql):
                violations = []
                which = stmt_node.WhichOneof("node")
                if which != "alter_table_stmt":
                    return violations
                alter = getattr(stmt_node, which)
                table_name = alter.relation.relname
                for cmd_node in alter.cmds:
                    cmd = _unwrap_node(cmd_node)
                    if cmd.subtype == pb.AT_DropColumn:
                        violations.append(Violation(
                            check_id=self.id,
                            severity=self.severity,
                            message=f"DROP COLUMN `{{cmd.name}}`",
                            hint="Ensure app code no longer references this column.",
                            statement_sql=raw_sql.strip(),
                            table=table_name,
                        ))
                return violations

        runner.register(DropColumnCheck())
        ```

        **Results ({len(_violations)} violations):**

{_format_violations(_violations)}
        """
    )
    return


if __name__ == "__main__":
    app.run()
