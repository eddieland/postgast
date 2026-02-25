"""Sphinx configuration for postgast documentation."""

import os
import sys

# Add src/ to path so Sphinx can import postgast modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

project = "postgast"
author = "Edward Jones"
copyright = "2025, Edward Jones"  # noqa: A001

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_llm.txt",
]

# Napoleon (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Theme
html_theme = "furo"
html_title = "postgast"

# Autodoc
autodoc_member_order = "bysource"
autodoc_typehints = "description"

# Mock the native ctypes module that loads the C library at import time.
# This allows Sphinx to document the pure-Python API without requiring
# the compiled libpg_query shared library.
autodoc_mock_imports = ["postgast.native"]

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "protobuf": ("https://googleapis.dev/python/protobuf/latest/", None),
}

# General
exclude_patterns = ["_build"]
