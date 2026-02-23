Contributing
============

See the `contributing guide on GitHub <https://github.com/eddieland/postgast/blob/main/CONTRIBUTING.md>`_
for full details on setting up a development environment, running tests, and
submitting pull requests.

Quick Start
-----------

.. code-block:: bash

   git clone https://github.com/eddieland/postgast.git
   cd postgast
   make install       # Install dependencies
   make build-native  # Compile vendored libpg_query
   make test          # Run tests

Development Commands
--------------------

.. code-block:: bash

   make fmt       # Autoformat (mdformat, codespell, ruff)
   make lint      # Format + type-check (basedpyright)
   make test      # Run tests
   make coverage  # Tests with coverage report
   make all       # install + lint + test
