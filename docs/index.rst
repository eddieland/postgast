postgast
========

BSD-licensed Python bindings to `libpg_query <https://github.com/pganalyze/libpg_query>`_,
the PostgreSQL parser extracted as a standalone C library.

Parse, deparse, normalize, fingerprint, split, and scan PostgreSQL SQL
statements from Python with a minimal dependency footprint — just ``protobuf``
and the vendored C library.

.. code-block:: python

   import postgast

   # Parse a query into an AST
   tree = postgast.parse("SELECT id, name FROM users WHERE active = true")

   # Deparse an AST back to SQL
   sql = postgast.deparse(tree)

   # Normalize a query (replace constants with placeholders)
   postgast.normalize("SELECT * FROM users WHERE id = 42")
   # => "SELECT * FROM users WHERE id = $1"

   # Fingerprint a query
   fp = postgast.fingerprint("SELECT * FROM users WHERE id = 42")

   # Split a multi-statement string
   postgast.split("SELECT 1; SELECT 2;")
   # => ["SELECT 1", "SELECT 2"]

Installation
------------

.. code-block:: bash

   pip install postgast

LLM-Friendly Docs
------------------

Machine-readable documentation is available for AI coding assistants:

- `llms.txt </llms.txt>`_ — concise overview
- `llms-full.txt </llms-full.txt>`_ — complete documentation in a single file

These files follow the `llms.txt standard <https://llmstxt.org/>`_.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   guide
   examples
   api
   architecture
   upgrade-policy
   contributing
