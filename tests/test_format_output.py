"""Expected output for format_sql — the "if I give A, I get B" reference.

Scan FORMAT_EXAMPLES to see exactly what format_sql produces for each input.
Each entry is (label, input_sql, expected_output).
"""

from __future__ import annotations

from textwrap import dedent

import pytest

from postgast import format_sql

FORMAT_EXAMPLES: list[tuple[str, str, str]] = [
    # -- Basic SELECT ------------------------------------------------
    (
        "select_literal",
        "SELECT 1",
        dedent("""\
            SELECT
              1;"""),
    ),
    (
        "select_columns",
        "SELECT a, b, c FROM t",
        dedent("""\
            SELECT
              a,
              b,
              c
            FROM
              t;"""),
    ),
    (
        "select_star_where",
        "SELECT * FROM users WHERE active = true",
        dedent("""\
            SELECT
              *
            FROM
              users
            WHERE
              active = TRUE;"""),
    ),
    (
        "select_alias",
        "SELECT a AS x, b AS y FROM t",
        dedent("""\
            SELECT
              a AS x,
              b AS y
            FROM
              t;"""),
    ),
    (
        "select_distinct",
        "SELECT DISTINCT a, b FROM t",
        dedent("""\
            SELECT DISTINCT
              a,
              b
            FROM
              t;"""),
    ),
    # -- WHERE expressions -------------------------------------------
    (
        "where_and",
        "SELECT * FROM t WHERE a = 1 AND b = 2 AND c = 3",
        dedent("""\
            SELECT
              *
            FROM
              t
            WHERE
              a = 1
              AND b = 2
              AND c = 3;"""),
    ),
    (
        "where_in",
        "SELECT * FROM t WHERE x IN (1, 2, 3)",
        dedent("""\
            SELECT
              *
            FROM
              t
            WHERE
              x IN (1, 2, 3);"""),
    ),
    (
        "where_between",
        "SELECT * FROM t WHERE x BETWEEN 1 AND 10",
        dedent("""\
            SELECT
              *
            FROM
              t
            WHERE
              x BETWEEN 1 AND 10;"""),
    ),
    (
        "where_exists",
        "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM s WHERE s.id = t.id)",
        dedent("""\
            SELECT
              *
            FROM
              t
            WHERE
              EXISTS (
                SELECT
                  1
                FROM
                  s
                WHERE
                  s.id = t.id
              );"""),
    ),
    # -- Expressions -------------------------------------------------
    (
        "case_expression",
        "SELECT CASE WHEN status = 1 THEN 'active' WHEN status = 2 THEN 'inactive' ELSE 'unknown' END AS label FROM users",
        dedent("""\
            SELECT
              CASE
                WHEN status = 1 THEN 'active'
                WHEN status = 2 THEN 'inactive'
                ELSE 'unknown'
              END AS label
            FROM
              users;"""),
    ),
    (
        "coalesce",
        "SELECT COALESCE(a, b, 0) FROM t",
        dedent("""\
            SELECT
              COALESCE(a, b, 0)
            FROM
              t;"""),
    ),
    (
        "window_function",
        "SELECT row_number() OVER (PARTITION BY dept ORDER BY salary DESC) FROM employees",
        dedent("""\
            SELECT
              row_number() OVER (PARTITION BY dept ORDER BY salary DESC)
            FROM
              employees;"""),
    ),
    # -- JOINs -------------------------------------------------------
    (
        "inner_join",
        "SELECT * FROM users JOIN orders ON users.id = orders.user_id",
        dedent("""\
            SELECT
              *
            FROM
              users
              JOIN orders ON users.id = orders.user_id;"""),
    ),
    (
        "multiple_left_joins",
        "SELECT * FROM a LEFT JOIN b ON a.id = b.a_id LEFT JOIN c ON b.id = c.b_id",
        dedent("""\
            SELECT
              *
            FROM
              a
              LEFT JOIN b ON a.id = b.a_id
              LEFT JOIN c ON b.id = c.b_id;"""),
    ),
    # -- ORDER BY / LIMIT / OFFSET -----------------------------------
    (
        "order_by",
        "SELECT * FROM t ORDER BY a ASC, b DESC NULLS LAST",
        dedent("""\
            SELECT
              *
            FROM
              t
            ORDER BY
              a ASC,
              b DESC NULLS LAST;"""),
    ),
    # -- Full SELECT kitchen sink ------------------------------------
    (
        "full_select",
        (
            "SELECT u.name, count(*) FROM users u "
            "JOIN orders o ON u.id = o.user_id "
            "WHERE o.total > 100 "
            "GROUP BY u.name "
            "HAVING count(*) > 1 "
            "ORDER BY u.name "
            "LIMIT 10"
        ),
        dedent("""\
            SELECT
              u.name,
              count(*)
            FROM
              users u
              JOIN orders o ON u.id = o.user_id
            WHERE
              o.total > 100
            GROUP BY
              u.name
            HAVING
              count(*) > 1
            ORDER BY
              u.name
            LIMIT
              10;"""),
    ),
    # -- CTEs --------------------------------------------------------
    (
        "cte",
        "WITH active AS (SELECT * FROM users WHERE active = true) SELECT * FROM active",
        dedent("""\
            WITH
              active AS (
                SELECT
                  *
                FROM
                  users
                WHERE
                  active = TRUE
              )
            SELECT
              *
            FROM
              active;"""),
    ),
    (
        "recursive_cte",
        "WITH RECURSIVE cnt AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM cnt WHERE n < 10) SELECT n FROM cnt",
        dedent("""\
            WITH RECURSIVE
              cnt AS (
                SELECT
                  1 AS n
                UNION ALL
                SELECT
                  n + 1
                FROM
                  cnt
                WHERE
                  n < 10
              )
            SELECT
              n
            FROM
              cnt;"""),
    ),
    # -- Set operations ----------------------------------------------
    (
        "union_all",
        "SELECT id FROM users UNION ALL SELECT id FROM admins",
        dedent("""\
            SELECT
              id
            FROM
              users
            UNION ALL
            SELECT
              id
            FROM
              admins;"""),
    ),
    # -- INSERT ------------------------------------------------------
    (
        "insert_values",
        "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')",
        dedent("""\
            INSERT INTO users (name, email)
            VALUES
              ('Alice', 'alice@example.com');"""),
    ),
    (
        "insert_on_conflict_update",
        "INSERT INTO t (a, b) VALUES (1, 2) ON CONFLICT (a) DO UPDATE SET b = EXCLUDED.b",
        dedent("""\
            INSERT INTO t (a, b)
            VALUES
              (1, 2)
            ON CONFLICT (a) DO UPDATE
            SET
              b = excluded.b;"""),
    ),
    # -- UPDATE ------------------------------------------------------
    (
        "update",
        "UPDATE users SET name = 'foo', active = false WHERE id = 1",
        dedent("""\
            UPDATE users
            SET
              name = 'foo',
              active = FALSE
            WHERE
              id = 1;"""),
    ),
    # -- DELETE ------------------------------------------------------
    (
        "delete",
        "DELETE FROM users WHERE created_at < '2020-01-01'",
        dedent("""\
            DELETE FROM users
            WHERE
              created_at < '2020-01-01';"""),
    ),
    (
        "delete_using",
        "DELETE FROM orders USING users WHERE orders.user_id = users.id AND users.active = false",
        dedent("""\
            DELETE FROM orders
            USING
              users
            WHERE
              orders.user_id = users.id
              AND users.active = FALSE;"""),
    ),
    # -- DDL ---------------------------------------------------------
    (
        "create_table",
        "CREATE TABLE users (id serial PRIMARY KEY, name text NOT NULL, email text UNIQUE)",
        dedent("""\
            CREATE TABLE users (
              id serial PRIMARY KEY,
              name TEXT NOT NULL,
              email TEXT UNIQUE
            );"""),
    ),
    (
        "create_index",
        "CREATE INDEX idx_users_name ON users (name)",
        "CREATE INDEX idx_users_name ON users (name);",
    ),
    (
        "alter_table",
        "ALTER TABLE users ADD COLUMN age integer",
        dedent("""\
            ALTER TABLE users
              ADD COLUMN age INTEGER;"""),
    ),
    (
        "drop_table",
        "DROP TABLE IF EXISTS users CASCADE",
        "DROP TABLE IF EXISTS users CASCADE;",
    ),
    # -- Multiple statements -----------------------------------------
    (
        "multi_statement",
        "SELECT 1; SELECT 2",
        dedent("""\
            SELECT
              1;

            SELECT
              2;"""),
    ),
]


@pytest.mark.parametrize(
    ("label", "input_sql", "expected"),
    FORMAT_EXAMPLES,
    ids=[e[0] for e in FORMAT_EXAMPLES],
)
def test_format_output(label: str, input_sql: str, expected: str) -> None:
    """format_sql(input_sql) produces exactly the expected output."""
    assert format_sql(input_sql) == expected
