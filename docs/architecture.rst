Architecture
============

This page covers the main technical decisions behind ``postgast``.

Why ctypes (not Cython, Rust, or C extensions)
-----------------------------------------------

``postgast`` binds to ``libpg_query`` with Python's built-in ``ctypes``
module. It does not use Cython, PyO3/Rust, or a hand-written CPython C
extension. The sections below give the reasons.

Pure-Python packaging
^^^^^^^^^^^^^^^^^^^^^

With ``ctypes``, the only compiled artifact is the vendored ``libpg_query``
shared library. Every layer above that library is plain Python. That includes
the struct definitions, the function signatures, the error handling, and the
protobuf deserialization. Three results follow.

- **No compiler toolchain at install time.** Nobody needs Cython, a Rust
  toolchain, or a C compiler to install ``postgast``. ``pip install postgast``
  delivers a pre-built wheel. That wheel holds the shared library and the pure
  Python code.
- **A smaller CI matrix.** Each platform build compiles one C library,
  ``libpg_query``. There is no second compilation step for a Python extension
  module. That removes a class of ABI compatibility problems, such as the
  limited API, the stable ABI, and per-interpreter builds.
- **Easier debugging.** Every line between the C boundary and the public API
  is Python that you can read. You can step through ``native.py`` with a
  normal debugger. No mixed C and Python stack frames appear.

Few dependencies
^^^^^^^^^^^^^^^^

``postgast`` declares one runtime dependency, ``protobuf``. It has no
build-time dependency on Cython or ``setuptools-rust``, no transitive
dependency on ``cffi``, and no compiled glue code. Fewer components mean fewer
ways for an install to fail.

BSD licensing
^^^^^^^^^^^^^

``pglast`` is the most established ``libpg_query`` wrapper for Python. It uses
the GPLv3 license. That license blocks ``pglast`` from many commercial
projects and from many permissively licensed projects. ``postgast`` keeps the
binding layer to ``ctypes`` (from the standard library) and ``protobuf``
(a BSD-compatible license). ``postgast`` can therefore ship under the BSD
2-Clause license with no copyleft obligation.

Trade-offs
^^^^^^^^^^

``ctypes`` also has costs.

- **No compile-time type checking at the C boundary.** A change to the
  ``libpg_query`` struct layout breaks the ctypes bindings. The build still
  succeeds. The break appears at runtime, and it is silent. ``postgast`` pins
  one ``libpg_query`` version and tests every platform in CI to limit this
  risk.
- **Per-call overhead.** A ``ctypes`` call costs more than a direct C
  extension call. The difference is small. ``libpg_query`` does the real work,
  because it parses the full PostgreSQL grammar. The ``ctypes`` marshalling
  cost stays far below the parse cost.
- **Manual struct definitions.** The ctypes ``Structure`` classes in
  ``native.py`` must mirror the C structs exactly. That is about 200 lines of
  hand-maintained code. A Cython ``.pxd`` file or Rust ``bindgen`` would
  generate these lines, at the cost of the toolchain described above.

``postgast`` accepts these costs in exchange for a simpler build, wider
portability, and a permissive license.

How the binding layer works
---------------------------

One internal module, ``native.py``, holds all C interop. It does three things.

1. **It loads the shared library.** It first looks for a vendored copy inside
   the wheel. If that copy is absent, it calls ``ctypes.util.find_library`` to
   locate a system library.
2. **It defines ctypes Structure classes.** These classes mirror every
   ``libpg_query`` result type, such as ``PgQueryParseResult`` and
   ``PgQueryNormalizeResult``.
3. **It declares function signatures.** Each public C function gets an
   ``argtypes`` value and a ``restype`` value. Python then checks the types of
   every call.

The higher-level modules (``parse.py``, ``deparse.py``, ``normalize.py``, and
the rest) import ``native.lib``. They all follow the same pattern:

.. code-block:: python

   # Pseudocode (actual code is in each module)
   result = native.lib.pg_query_parse_protobuf(sql.encode())
   try:
       check_error(result)       # raise PgQueryError if result.error is set
       payload = extract(result) # read return value
   finally:
       native.lib.pg_query_free_protobuf_parse_result(result)

The ``finally`` block always frees the C-allocated memory, even when the code
raises an error.

Protobuf deserialization
^^^^^^^^^^^^^^^^^^^^^^^^

``libpg_query`` returns each parse tree as a serialized Protocol Buffer
message. ``postgast`` deserializes that message with the official ``protobuf``
library into the message classes in ``pg_query_pb2``. ``postgast`` builds those
classes at import time from a descriptor set that it ships
(``pg_query.desc``). An install therefore never runs ``protoc``. This approach
avoids a custom deserializer, and it tracks the upstream ``.proto`` schema
exactly.

``postgast`` reads binary payloads with ``ctypes.string_at(data, length)``
instead of ``c_char_p``. Protobuf data can contain embedded null bytes, and
``c_char_p`` truncates the payload at the first null byte.

Alternatives considered
-----------------------

Cython
^^^^^^

Cython gives compile-time type safety at the C boundary and a slightly lower
call overhead. It also requires a C compiler at wheel build time, and it adds
a Cython build dependency. The binding layer is about 200 lines of struct
definitions and function signatures. That size does not justify the added
build complexity.

Rust (PyO3 / maturin)
^^^^^^^^^^^^^^^^^^^^^^

A Rust extension through PyO3 provides memory safety and strong typing.
``libpg_query`` is a C library, so the Rust layer still calls C through FFI.
Rust also adds a second toolchain (``cargo``) and the ``maturin`` build
backend, and it makes cross-compilation harder. The binding layer is too small
to gain from Rust.

CFFI
^^^^

CFFI is a common alternative to ``ctypes``. It offers an ABI mode, which
resembles ``ctypes``, and an API mode, which generates a C extension. ABI mode
gives ``postgast`` no advantage over ``ctypes``. API mode reintroduces the C
compiler requirement. ``postgast`` therefore stays with ``ctypes`` and adds no
``cffi`` dependency.

Hand-written CPython C extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A C extension is the fastest option. It also ties the code to CPython
internals and requires careful reference counting. It makes a wheel build for
several Python versions harder. The speed difference does not matter for this
library's workload.
