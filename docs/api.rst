API Reference
=============

Core Functions
--------------

.. autofunction:: postgast.parse

.. autofunction:: postgast.deparse

.. autofunction:: postgast.normalize

.. autofunction:: postgast.fingerprint

.. autofunction:: postgast.split

.. autofunction:: postgast.scan

Tree Walking
------------

.. autofunction:: postgast.walk

.. autoclass:: postgast.Visitor
   :members:

AST Helpers
-----------

.. autofunction:: postgast.find_nodes

.. autofunction:: postgast.extract_tables

.. autofunction:: postgast.extract_columns

.. autofunction:: postgast.extract_functions

.. autofunction:: postgast.extract_function_identity

.. autofunction:: postgast.extract_trigger_identity

DDL Helpers
-----------

.. autofunction:: postgast.set_or_replace

.. autofunction:: postgast.ensure_or_replace

.. autofunction:: postgast.to_drop

Types
-----

.. autoclass:: postgast.FingerprintResult

.. autoclass:: postgast.FunctionIdentity

.. autoclass:: postgast.TriggerIdentity

Exceptions
----------

.. autoclass:: postgast.PgQueryError
   :members:
