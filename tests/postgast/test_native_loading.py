import ctypes
import ctypes.util
import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _import_native():
    """Import (or re-import) _native with a fresh module state."""
    mod_name = "postgast.native"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


class TestVendoredFirst:
    def test_loads_vendored_when_present(self):
        mock_cdll = MagicMock()
        with (
            patch("platform.system", return_value="Linux"),
            patch.object(Path, "is_file", return_value=True),
            patch.object(ctypes, "CDLL", return_value=mock_cdll) as cdll_call,
        ):
            mod = _import_native()

        assert mod.lib is mock_cdll
        call_arg = cdll_call.call_args[0][0]
        assert call_arg.endswith("libpg_query.so")


class TestSystemFallback:
    def test_falls_back_to_system_library(self):
        mock_cdll = MagicMock()
        with (
            patch("platform.system", return_value="Linux"),
            patch.object(Path, "is_file", return_value=False),
            patch.object(ctypes.util, "find_library", return_value="/usr/lib/libpg_query.so"),
            patch.object(ctypes, "CDLL", return_value=mock_cdll) as cdll_call,
        ):
            mod = _import_native()

        assert mod.lib is mock_cdll
        cdll_call.assert_called_once_with("/usr/lib/libpg_query.so")


class TestLoadFailure:
    def test_raises_oserror_when_not_found(self):
        with (
            patch("platform.system", return_value="Linux"),
            patch.object(Path, "is_file", return_value=False),
            patch.object(ctypes.util, "find_library", return_value=None),
        ):
            with pytest.raises(OSError, match="libpg_query shared library not found"):
                _import_native()
