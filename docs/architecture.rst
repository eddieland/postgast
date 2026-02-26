Architecture
============

This page explains the key technical decisions behind ``postgast`` and why
they were made.

Why ctypes (not Cython, Rust, or C extensions)
-----------------------------------------------

``postgast`` binds to ``libpg_query`` using Python's built-in ``ctypes``
module rather than Cython, PyO3/Rust, or a hand-written CPython C extension.
This was a deliberate choice — here is the reasoning.

Pure-Python packaging
^^^^^^^^^^^^^^^^^^^^^

With ``ctypes`` the only compiled artifact is the vendored ``libpg_query``
shared library itself.  Everything above it — struct definitions, function
signatures, error handling, protobuf deserialization — is plain Python.  This
means:

- **No compiler toolchain at install time.**  Users never need Cython, a Rust
  toolchain, or a C compiler to install ``postgast``.  ``pip install postgast``
  delivers a pre-built wheel containing the shared library and pure-Python
  code.
- **Simpler CI matrix.**  Wheels are built by compiling a single C library
  (``libpg_query``) per platform.  There is no second compilation step for a
  Python extension module, which removes an entire class of ABI-compatibility
  issues (limited API, stable ABI, per-interpreter builds, etc.).
- **Easier debugging.**  Every line between the C boundary and the public API
  is inspectable Python.  A developer can step through ``native.py`` with a
  normal debugger — no mixed C/Python stack frames.

Minimal dependency footprint
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The only runtime dependency is ``protobuf``.  There is no build-time
dependency on Cython or ``setuptools-rust``, no transitive dependency on
``cffi``, and no compiled glue code.  Fewer moving parts means fewer ways the
install can break.

BSD licensing
^^^^^^^^^^^^^

``pglast``, the most established ``libpg_query`` wrapper for Python, is
licensed under GPLv3.  This makes it unusable in many commercial and
permissively-licensed projects.  By keeping the binding layer to ``ctypes``
(stdlib) plus ``protobuf`` (BSD-compatible), ``postgast`` can ship under the
BSD 2-Clause license with no copyleft obligations.

Trade-offs
^^^^^^^^^^

Using ``ctypes`` is not free of downsides:

- **No compile-time type checking at the C boundary.**  If the
  ``libpg_query`` struct layout changes between versions the ctypes bindings
  break silently at runtime rather than failing to compile.  This is mitigated
  by pinning to a specific ``libpg_query`` version and testing across
  platforms in CI.
- **Per-call overhead.**  Each ``ctypes`` call has slightly more overhead than
  a direct C extension call.  In practice this is negligible because the real
  work happens inside ``libpg_query`` (parsing a full PostgreSQL grammar) and
  the ``ctypes`` marshalling cost is dwarfed by the parser itself.
- **Manual struct definitions.**  The ctypes ``Structure`` classes in
  ``native.py`` must mirror the C structs exactly.  This is a small amount of
  code (~200 lines) maintained by hand.  A Cython ``.pxd`` or Rust
  ``bindgen`` would generate these, but at the cost of the toolchain
  complexity described above.

On balance the simplicity, portability, and licensing benefits outweigh the
minor ergonomic costs.

How the binding layer works
---------------------------

All C interop lives in a single internal module, ``native.py``.  It:

1. **Loads the shared library** — first checking for a vendored copy bundled
   in the wheel, then falling back to ``ctypes.util.find_library`` for
   system-installed libraries.
2. **Defines ctypes** ``Structure`` **classes** that mirror every
   ``libpg_query`` result type (``PgQueryParseResult``,
   ``PgQueryNormalizeResult``, etc.).
3. **Declares function signatures** (``argtypes`` / ``restype``) for each
   public C function so that calls are type-checked at the Python level.

Higher-level modules (``parse.py``, ``deparse.py``, ``normalize.py``, …)
import ``native.lib`` and follow a consistent pattern:

.. code-block:: python

   # Pseudocode — actual code is in each module
   result = native.lib.pg_query_parse_protobuf(sql.encode())
   try:
       check_error(result)       # raise PgQueryError if result.error is set
       payload = extract(result) # read return value
   finally:
       native.lib.pg_query_free_protobuf_parse_result(result)

The ``finally`` block ensures the C-allocated memory is always freed, even
when an error is raised.

Protobuf deserialization
^^^^^^^^^^^^^^^^^^^^^^^^

``libpg_query`` returns parse trees as serialized Protocol Buffer messages.
``postgast`` deserializes them using the official ``protobuf`` library into
generated Python message classes (``pg_query_pb2``).  This avoids writing a
custom deserializer and tracks the upstream ``.proto`` schema exactly.

Binary payloads are read with ``ctypes.string_at(data, length)`` rather than
``c_char_p`` because protobuf data can contain embedded null bytes that
``c_char_p`` would silently truncate.

Alternatives considered
-----------------------

Cython
^^^^^^

Cython would give compile-time type safety at the C boundary and marginally
faster call overhead.  However it requires a C compiler at wheel-build time
*and* introduces a Cython build dependency.  For a thin binding layer (~200
lines of struct definitions and function signatures), the added build
complexity is not justified.

Rust (PyO3 / maturin)
^^^^^^^^^^^^^^^^^^^^^^

A Rust extension via PyO3 would provide memory safety guarantees and strong
typing.  However ``libpg_query`` is a C library — the Rust layer would still
call C via FFI.  Adding Rust introduces a second toolchain (``cargo``), a
``maturin`` build backend, and complicates cross-compilation.  The binding
layer is too thin to benefit from Rust's strengths.

CFFI
^^^^

CFFI is a popular alternative to ``ctypes`` that offers an ABI mode (similar
to ``ctypes``) and an API mode (generates a C extension).  ABI mode provides
no advantage over ``ctypes`` for this use case, and API mode reintroduces the
C compiler requirement.  Staying with ``ctypes`` avoids adding ``cffi`` as a
dependency.

Hand-written CPython C extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A C extension would be the fastest option, but it ties the code to CPython
internals, requires careful reference counting, and complicates building
wheels for multiple Python versions.  The performance difference is immaterial
for this library's workload.
