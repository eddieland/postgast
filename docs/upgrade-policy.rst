Upgrade Policy
==============

This page describes how ``postgast`` tracks upstream dependencies. It also
lists the supported Python versions.

Python
------

``postgast`` supports **Python 3.10** through the latest GA release, which is
3.14.

A future release raises the minimum version to **Python 3.12**. That release
also raises the ``postgast`` major version, which signals the change. Pin
``postgast<2`` if you must remain on Python 3.10 or 3.11.

PostgreSQL (libpg_query)
------------------------

``postgast`` always vendors the latest available version of
`libpg_query <https://github.com/pganalyze/libpg_query>`_. The vendored
version sets the PostgreSQL grammar for every operation.

``postgast`` delegates every parse to ``libpg_query``. The vendored library
version therefore sets the PostgreSQL syntax that ``postgast`` accepts.
``postgast`` has no separate PostgreSQL version setting.

The PostgreSQL parser rarely makes a backwards-incompatible change. A
``libpg_query`` upgrade usually adds *new* syntax and keeps existing syntax
valid. To hold one parser version, pin the ``postgast`` version that vendors
it.

Versioning
----------

``postgast`` follows `Semantic Versioning <https://semver.org/>`_:

- **Patch** releases contain bug fixes and ``libpg_query`` patch updates.
- **Minor** releases add new features or upgrade ``libpg_query`` to a new
  PostgreSQL major version.
- **Major** releases include breaking API changes or Python support-range
  changes (such as dropping a Python version).

What this means in practice
---------------------------

- **Most users** can track the latest ``postgast`` release. A ``libpg_query``
  parser upgrade almost never breaks existing SQL.
- **Users on older Python versions** should pin the last major version that
  supports their interpreter after the minimum rises.
- **Users who need one PostgreSQL parser version** should pin the ``postgast``
  version that vendors the matching ``libpg_query`` release.
