Common Usage Patterns
=====================

This page demonstrates practical patterns for common tasks. For API
fundamentals, see the :doc:`guide`.

.. contents:: On this page
   :local:
   :depth: 2

Query Analysis
--------------

Audit which tables a query touches
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import postgast

   sql = """
       SELECT o.id, c.name, p.title
       FROM orders o
       JOIN customers c ON o.customer_id = c.id
       JOIN products p ON o.product_id = p.id
       WHERE o.created_at > '2024-01-01'
   """
   tree = postgast.parse(sql)

   tables = postgast.extract_tables(tree)
   columns = postgast.extract_columns(tree)
   functions = postgast.extract_functions(tree)

   print("Tables:", tables)    # ['orders', 'customers', 'products']
   print("Columns:", columns)  # ['o.id', 'c.name', 'p.title', ...]
   print("Functions:", functions)  # []

Detect queries that use subqueries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from postgast import parse, find_nodes
   from postgast.pg_query_pb2 import SelectStmt

   def has_subquery(sql: str) -> bool:
       """Return True if the SQL contains a nested SELECT."""
       tree = parse(sql)
       select_count = sum(1 for _ in find_nodes(tree, SelectStmt))
       return select_count > 1

   has_subquery("SELECT * FROM users")
   # => False

   has_subquery("SELECT * FROM (SELECT id FROM users) AS sub")
   # => True

Find all function calls in a query
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import postgast

   sql = "SELECT upper(name), count(*) FROM users GROUP BY upper(name)"
   tree = postgast.parse(sql)

   print(postgast.extract_functions(tree))
   # ['upper', 'count', 'upper']

   # Unique function names:
   print(set(postgast.extract_functions(tree)))
   # {'upper', 'count'}

Query Monitoring
----------------

Group queries with normalization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace literal values with positional placeholders so that structurally
identical queries collapse into a single group:

.. code-block:: python

   import postgast

   queries = [
       "SELECT * FROM users WHERE id = 42",
       "SELECT * FROM users WHERE id = 99",
       "SELECT * FROM orders WHERE status = 'pending'",
   ]

   for q in queries:
       print(postgast.normalize(q))
   # SELECT * FROM users WHERE id = $1
   # SELECT * FROM users WHERE id = $1
   # SELECT * FROM orders WHERE status = $1

Fingerprint queries for deduplication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Two queries are structurally equivalent when they have the same fingerprint,
regardless of literal values, whitespace, or formatting:

.. code-block:: python

   import postgast

   fp1 = postgast.fingerprint("SELECT * FROM users WHERE id = 1")
   fp2 = postgast.fingerprint("select  *  from  users  where  id = 999")

   assert fp1.hex == fp2.hex  # same structure

   fp3 = postgast.fingerprint("SELECT * FROM orders WHERE id = 1")
   assert fp1.hex != fp3.hex  # different table

SQL Formatting
--------------

Pretty-print SQL
^^^^^^^^^^^^^^^^^

.. code-block:: python

   import postgast

   ugly = "select u.id,u.name,o.total from users u join orders o on u.id=o.user_id where o.total>100 order by o.total desc"
   print(postgast.format_sql(ugly))

Output:

.. code-block:: sql

   SELECT
     u.id,
     u.name,
     o.total
   FROM
     users u
     JOIN orders o ON u.id = o.user_id
   WHERE
     o.total > 100
   ORDER BY
     o.total DESC;

Format an already-parsed tree
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``format_sql`` also accepts a ``ParseResult``, so you can format after
making AST modifications:

.. code-block:: python

   import postgast

   tree = postgast.parse("CREATE VIEW v AS SELECT 1")
   postgast.set_or_replace(tree)
   print(postgast.format_sql(tree))

Output:

.. code-block:: sql

   CREATE OR REPLACE VIEW v AS
   SELECT
     1;

Batch Processing
----------------

Process a SQL migration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :func:`~postgast.split` to break a multi-statement file into individual
statements, then analyze each one:

.. code-block:: python

   import postgast

   migration = """
       CREATE TABLE users (
           id serial PRIMARY KEY,
           name text NOT NULL
       );

       CREATE INDEX idx_users_name ON users (name);

       INSERT INTO users (name) VALUES ('alice'), ('bob');
   """

   for stmt in postgast.split(migration):
       tree = postgast.parse(stmt)
       tables = postgast.extract_tables(tree)
       print(f"Tables: {tables!r:30s}  SQL: {stmt.strip()[:60]}...")

Split with tolerance for invalid SQL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``"scanner"`` method splits on semicolons without parsing, so it works
even when the SQL contains syntax errors:

.. code-block:: python

   import postgast

   broken = "SELECT 1; INVALID SYNTAX HERE; SELECT 2"
   stmts = postgast.split(broken, method="scanner")
   print(stmts)
   # ['SELECT 1', ' INVALID SYNTAX HERE', ' SELECT 2']

DDL Tooling
-----------

Generate rollback DROP statements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Automatically produce ``DROP`` statements from ``CREATE`` DDL for migration
rollback scripts:

.. code-block:: python

   import postgast

   creates = [
       "CREATE FUNCTION public.add(a int, b int) RETURNS int LANGUAGE sql AS $$ SELECT a + b $$",
       "CREATE VIEW active_users AS SELECT * FROM users WHERE active",
       "CREATE TRIGGER audit_trg BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION audit()",
   ]

   for sql in creates:
       print(postgast.to_drop(sql))
   # DROP FUNCTION public.add(int, int)
   # DROP VIEW active_users
   # DROP TRIGGER audit_trg ON users

Make CREATE statements idempotent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add ``OR REPLACE`` to ``CREATE FUNCTION``, ``CREATE TRIGGER``, and
``CREATE VIEW`` statements so they can be re-run safely:

.. code-block:: python

   import postgast

   sql = "CREATE VIEW active_users AS SELECT * FROM users WHERE active"
   print(postgast.ensure_or_replace(sql))
   # CREATE OR REPLACE VIEW active_users AS SELECT * FROM users WHERE active = true

   # Already idempotent input is unchanged:
   postgast.ensure_or_replace(postgast.ensure_or_replace(sql))

Tree Walking
------------

Walk the AST to inspect structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`~postgast.walk` yields every node in the tree with its parent field
name, useful for debugging or generic transforms:

.. code-block:: python

   import postgast

   tree = postgast.parse("SELECT a FROM t WHERE x = 1")
   for field_name, node in postgast.walk(tree):
       if field_name:
           print(f"  {field_name}: {type(node).__name__}")

Output::

     stmts: RawStmt
     stmt: SelectStmt
     target_list: ResTarget
     val: ColumnRef
     fields: String
     from_clause: RangeVar
     where_clause: A_Expr
     lexpr: ColumnRef
     fields: String
     rexpr: A_Const

Collect information with the Visitor pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a :class:`~postgast.Visitor` subclass with ``visit_<TypeName>``
methods. Unhandled node types automatically recurse into their children:

.. code-block:: python

   import postgast

   class QueryAnalyzer(postgast.Visitor):
       def __init__(self):
           self.tables = []
           self.columns = []
           self.has_where = False

       def visit_RangeVar(self, node):
           self.tables.append(node.relname)

       def visit_ColumnRef(self, node):
           parts = []
           for f in node.fields:
               inner = getattr(f, f.WhichOneof("node"))
               if hasattr(inner, "sval"):
                   parts.append(inner.sval)
           self.columns.append(".".join(parts))

       def visit_SelectStmt(self, node):
           if node.HasField("where_clause"):
               self.has_where = True
           self.generic_visit(node)  # continue into children

   tree = postgast.parse("SELECT u.name FROM users u WHERE u.active = true")
   analyzer = QueryAnalyzer()
   analyzer.visit(tree)

   print(analyzer.tables)     # ['users']
   print(analyzer.columns)    # ['u.name', 'u.active']
   print(analyzer.has_where)  # True

Control traversal depth
^^^^^^^^^^^^^^^^^^^^^^^^

Omitting the call to ``self.generic_visit(node)`` in a handler stops
recursion into that node's children. This lets you skip subtrees:

.. code-block:: python

   import postgast

   class TopLevelTables(postgast.Visitor):
       """Collect tables from the top-level FROM clause only, ignoring subqueries."""

       def __init__(self):
           self.tables = []

       def visit_RangeVar(self, node):
           self.tables.append(node.relname)

       def visit_SubLink(self, _node):
           pass  # don't recurse into subqueries

   tree = postgast.parse(
       "SELECT * FROM orders WHERE customer_id IN (SELECT id FROM vip_customers)"
   )
   v = TopLevelTables()
   v.visit(tree)
   print(v.tables)  # ['orders'] — vip_customers is skipped

Use typed AST wrappers
^^^^^^^^^^^^^^^^^^^^^^^

Wrap a parse tree with :func:`~postgast.wrap` for typed attribute access.
Works with :func:`~postgast.walk_typed` and :class:`~postgast.TypedVisitor`:

.. code-block:: python

   from postgast import parse, wrap, walk_typed, TypedVisitor

   tree = wrap(parse("SELECT a, b FROM t"))
   for field_name, node in walk_typed(tree):
       if field_name:
           print(f"  {field_name}: {type(node).__name__}")

Working with the Protobuf AST
------------------------------

Access raw protobuf nodes
^^^^^^^^^^^^^^^^^^^^^^^^^^

The parse tree is a standard protobuf ``Message``. You can inspect it
using all the usual protobuf APIs:

.. code-block:: python

   import postgast

   tree = postgast.parse("SELECT id, name FROM users WHERE active = true")

   # Navigate to the SelectStmt
   raw_stmt = tree.stmts[0]
   select = raw_stmt.stmt.select_stmt

   # Inspect the target list (SELECT columns)
   for target in select.target_list:
       col = target.res_target.val.column_ref
       name = col.fields[0].string.sval
       print(f"Column: {name}")

   # Inspect the FROM clause
   table = select.from_clause[0].range_var
   print(f"Table: {table.relname}")  # 'users'

Find specific node types
^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`~postgast.find_nodes` filters the walk to a single protobuf
message type:

.. code-block:: python

   from postgast import parse, find_nodes
   from postgast.pg_query_pb2 import FuncCall, RangeVar

   tree = parse("SELECT lower(name), count(*) FROM users GROUP BY lower(name)")

   # All table references
   for rv in find_nodes(tree, RangeVar):
       print(f"Table: {rv.relname}")

   # All function calls
   for fc in find_nodes(tree, FuncCall):
       func_name = fc.funcname[0].string.sval
       print(f"Function: {func_name}")

PL/pgSQL Parsing
-----------------

Parse a PL/pgSQL function body
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`~postgast.parse_plpgsql` returns a structured representation of a
PL/pgSQL function's body, including declarations, assignments, and control
flow:

.. code-block:: python

   import json
   import postgast

   sql = """
       CREATE FUNCTION greet(name text) RETURNS text LANGUAGE plpgsql AS $$
       DECLARE
           result text;
       BEGIN
           result := 'Hello, ' || name;
           RETURN result;
       END;
       $$
   """

   parsed = postgast.parse_plpgsql(sql)
   print(json.dumps(parsed, indent=2))

Error Handling
--------------

Catch and inspect parse errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All functions raise :class:`~postgast.PgQueryError` on invalid SQL. The
exception carries the error message, cursor position, and source location:

.. code-block:: python

   import postgast

   try:
       postgast.parse("SELECT * FORM users")
   except postgast.PgQueryError as e:
       print(f"Error: {e.message}")
       print(f"Position: {e.cursorpos}")
       # Error: syntax error at or near "users"
       # Position: 15

Validate SQL before execution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``parse`` as a fast syntax check without hitting the database:

.. code-block:: python

   import postgast

   def is_valid_sql(sql: str) -> bool:
       try:
           postgast.parse(sql)
           return True
       except postgast.PgQueryError:
           return False

   is_valid_sql("SELECT * FROM users")            # True
   is_valid_sql("SLECT * FORM users")             # False
   is_valid_sql("SELECT 1; DROP TABLE users; --") # True (valid SQL!)

Tokenization
-------------

Scan SQL into tokens
^^^^^^^^^^^^^^^^^^^^^

:func:`~postgast.scan` returns the raw token stream, useful for syntax
highlighting, keyword detection, or building custom splitters:

.. code-block:: python

   import postgast

   result = postgast.scan("SELECT id FROM users WHERE active = true")
   for token in result.tokens:
       # Extract the token text using byte positions
       text = "SELECT id FROM users WHERE active = true"[token.start:token.end]
       print(f"{text:12s}  token={token.token}  keyword={token.keyword_kind}")
