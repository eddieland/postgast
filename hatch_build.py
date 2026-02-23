"""Custom hatchling build hook that compiles libpg_query and bundles the shared library."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_LIB_NAMES = {
    "Linux": "libpg_query.so",
    "Darwin": "libpg_query.dylib",
    "Windows": "pg_query.dll",
}


class CustomBuildHook(BuildHookInterface):
    """Build hook that compiles libpg_query and includes it in the wheel."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Compile libpg_query and inject the shared library into the wheel."""
        root = Path(self.root)
        libpg_query_dir = root / "vendor" / "libpg_query"

        makefile = libpg_query_dir / "Makefile"
        if not makefile.exists():
            self.app.display_warning(
                "vendor/libpg_query/Makefile not found — skipping native library build. "
                "Run 'git submodule update --init' to fetch the source."
            )
            return

        system = platform.system()
        lib_name = _LIB_NAMES.get(system)
        if lib_name is None:
            msg = f"Unsupported platform: {system}"
            raise RuntimeError(msg)

        # Compile the shared library.
        if system == "Windows":
            subprocess.check_call(["nmake", "/F", "Makefile.msvc"], cwd=libpg_query_dir)
        else:
            subprocess.check_call(["make", "build_shared"], cwd=libpg_query_dir)

        lib_path = libpg_query_dir / lib_name
        if not lib_path.exists():
            msg = f"Expected shared library not found after build: {lib_path}"
            raise RuntimeError(msg)

        # Include the shared library in the wheel alongside the postgast package.
        build_data["force_include"][str(lib_path)] = f"postgast/{lib_name}"

        # Mark as platform-specific wheel (not pure Python).
        build_data["infer_tag"] = True
        build_data["pure_python"] = False

    def clean(self, versions: list[str]) -> None:
        """Remove compiled artifacts from the vendor directory."""
        root = Path(self.root)
        libpg_query_dir = root / "vendor" / "libpg_query"
        if libpg_query_dir.exists():
            subprocess.call(["make", "clean"], cwd=libpg_query_dir)
