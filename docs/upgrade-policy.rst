Upgrade Policy
==============

This page describes how ``postgast`` tracks upstream dependencies and which
Python versions are supported.

Python
------

``postgast`` currently supports **Python 3.10** through the latest GA release
(currently 3.14).

The minimum supported version will move to **Python 3.12** in an upcoming
release. When this happens the major version will be bumped to signal the
change. Pin ``postgast<2`` if you need to stay on Python 3.10 or 3.11.

PostgreSQL (libpg_query)
------------------------

``postgast`` always vendors the latest available version of
`libpg_query <https://github.com/pganalyze/libpg_query>`_. The vendored
version determines which PostgreSQL grammar is used for parsing, deparsing,
and all other operations.

Because ``postgast`` delegates all parsing to ``libpg_query``, the PostgreSQL
syntax it understands is dictated entirely by the vendored library version.
There is no separate PostgreSQL version knob to configure.

Backwards-incompatible changes to the PostgreSQL parser are exceedingly rare.
In practice a ``libpg_query`` upgrade means *new* syntax is accepted, not that
existing syntax breaks. Still, if you need to pin a specific parser version
you can pin the ``postgast`` version that vendors it.

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

- **Most users** can track the latest ``postgast`` release with no issues.
  ``libpg_query`` parser upgrades almost never break existing SQL.
- **Users on older Python versions** should pin to the last major version that
  supports their interpreter once the minimum is raised.
- **Users who need a specific PostgreSQL parser version** should pin the
  ``postgast`` version that vendors the corresponding ``libpg_query`` release.
