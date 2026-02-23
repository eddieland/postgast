User Guide
==========

Parsing
-------

Parse a SQL query into a protobuf AST:

.. code-block:: python

   import postgast

   tree = postgast.parse("SELECT id, name FROM users WHERE active = true")
   # tree.stmts[0] contains the first (and only) statement

The returned ``ParseResult`` is a protobuf message. Each statement in
``tree.stmts`` is a ``RawStmt`` wrapping a ``Node`` oneof.

Deparsing
---------

Convert a parse tree back into SQL text:

.. code-block:: python

   sql = postgast.deparse(tree)
   # "SELECT id, name FROM users WHERE active = true"

The deparsed SQL is canonicalized by libpg_query and may differ from the
original in whitespace, casing, or parenthesization while remaining
semantically equivalent.

Normalization
-------------

Replace literal constants with positional placeholders:

.. code-block:: python

   postgast.normalize("SELECT * FROM users WHERE id = 42 AND name = 'alice'")
   # => "SELECT * FROM users WHERE id = $1 AND name = $2"

This is useful for grouping structurally equivalent queries.

Fingerprinting
--------------

Compute a structural hash that identifies equivalent queries regardless of
literal values:

.. code-block:: python

   fp = postgast.fingerprint("SELECT * FROM users WHERE id = 42")
   fp.fingerprint  # uint64 hash
   fp.hex          # hex string representation

Splitting
---------

Split a multi-statement SQL string into individual statements:

.. code-block:: python

   postgast.split("SELECT 1; SELECT 2;")
   # => ["SELECT 1", "SELECT 2"]

Two methods are available via the ``method`` parameter:

- ``"parser"`` (default) — uses the full PostgreSQL parser for accuracy
- ``"scanner"`` — faster, tolerates invalid SQL

.. code-block:: python

   postgast.split("SELECT 1; SELECT 2;", method="scanner")

Scanning
--------

Tokenize a SQL string:

.. code-block:: python

   result = postgast.scan("SELECT 1")
   for token in result.tokens:
       print(token.token, token.keyword_kind, token.start, token.end)

Tree Walking
------------

Walk all nodes in a parse tree with depth-first traversal:

.. code-block:: python

   for field_name, node in postgast.walk(tree):
       print(type(node).__name__, field_name)

Or use the visitor pattern:

.. code-block:: python

   class TableCollector(postgast.Visitor):
       def __init__(self):
           self.tables = []

       def visit_RangeVar(self, node):
           self.tables.append(node.relname)

   collector = TableCollector()
   collector.visit(tree)
   print(collector.tables)

AST Helpers
-----------

Extract common information from parse trees:

.. code-block:: python

   tree = postgast.parse("SELECT u.id, u.name FROM users u JOIN orders o ON u.id = o.user_id")

   postgast.extract_tables(tree)    # ["users", "orders"]
   postgast.extract_columns(tree)   # ["u.id", "u.name", "u.id", "o.user_id"]
   postgast.extract_functions(tree) # []

Find specific node types:

.. code-block:: python

   from postgast.pg_query_pb2 import RangeVar

   for node in postgast.find_nodes(tree, RangeVar):
       print(node.relname, node.alias.aliasname if node.alias.aliasname else "")

DDL Helpers
-----------

Generate ``DROP`` statements from ``CREATE`` DDL:

.. code-block:: python

   postgast.to_drop("CREATE FUNCTION add(a int, b int) RETURNS int AS $$ SELECT a + b $$ LANGUAGE sql")
   # => "DROP FUNCTION add(int, int)"

Rewrite ``CREATE`` to ``CREATE OR REPLACE``:

.. code-block:: python

   postgast.ensure_or_replace("CREATE FUNCTION add(a int, b int) RETURNS int AS $$ SELECT a + b $$ LANGUAGE sql")
   # => "CREATE OR REPLACE FUNCTION ..."

Error Handling
--------------

All functions raise :class:`~postgast.PgQueryError` on invalid SQL:

.. code-block:: python

   try:
       postgast.parse("SELECT FROM")
   except postgast.PgQueryError as e:
       print(e.message)     # Error message
       print(e.cursorpos)   # Position in the SQL string
