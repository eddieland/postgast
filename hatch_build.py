"""Custom hatchling build hook that compiles libpg_query and bundles the shared library."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_LIB_NAMES = {
    "Linux": "libpg_query.so",
    "Darwin": "libpg_query.dylib",
    "Windows": "pg_query.dll",
}


def _cpu_count() -> int:
    """Return usable CPU count for parallel compilation."""
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


def _strip_shared_library(lib_path: Path, system: str) -> None:
    """Strip debug symbols from the shared library to reduce size.

    Silently skips if strip is unavailable (e.g. minimal containers).
    """
    if system == "Windows":
        return

    strip = shutil.which("strip")
    if strip is None:
        return

    cmd = [strip]
    if system == "Darwin":
        cmd.extend(["-x", str(lib_path)])
    else:
        cmd.extend(["--strip-debug", str(lib_path)])

    subprocess.run(cmd, check=False)


class CustomBuildHook(BuildHookInterface):
    """Build hook that compiles libpg_query and includes it in the wheel."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Compile libpg_query and inject the shared library into the wheel."""
        root = Path(self.root)
        libpg_query_dir = root / "vendor" / "libpg_query"

        # Check for Makefile to distinguish an empty submodule dir from a populated one.
        if not (libpg_query_dir / "Makefile").exists():
            self.app.display_warning(
                "vendor/libpg_query not found or submodule not initialized — skipping native library build. "
                "Run 'git submodule update --init' to fetch the source."
            )
            return

        system = platform.system()
        lib_name = _LIB_NAMES.get(system)
        if lib_name is None:
            msg = f"Unsupported platform: {system}"
            raise RuntimeError(msg)

        # Build environment: pass through user CFLAGS/MAKEFLAGS and add parallel jobs.
        env = os.environ.copy()
        if "MAKEFLAGS" not in env:
            env["MAKEFLAGS"] = f"-j{_cpu_count()}"

        # Compile the shared library.
        if system == "Windows":
            compile_cmd: list[str] = ["nmake", "/F", "Makefile.msvc"]
        else:
            compile_cmd = ["make", "build_shared"]

        result = subprocess.run(compile_cmd, cwd=libpg_query_dir, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            msg = f"libpg_query build failed (exit {result.returncode})"
            if result.stderr:
                msg += f":\n{result.stderr}"
            raise RuntimeError(msg)

        lib_path = libpg_query_dir / lib_name
        if not lib_path.exists():
            msg = f"Expected shared library not found after build: {lib_path}"
            raise RuntimeError(msg)

        # Strip debug symbols to reduce wheel size.
        _strip_shared_library(lib_path, system)

        # Include the shared library in the wheel alongside the postgast package.
        build_data["force_include"][str(lib_path)] = f"postgast/{lib_name}"

        # Mark as platform-specific wheel (not pure Python).
        build_data["infer_tag"] = True
        build_data["pure_python"] = False

    def clean(self, versions: list[str]) -> None:
        """Remove compiled artifacts from the vendor directory."""
        root = Path(self.root)
        libpg_query_dir = root / "vendor" / "libpg_query"
        if not (libpg_query_dir / "Makefile").exists():
            return

        if platform.system() == "Windows":
            subprocess.run(["nmake", "/F", "Makefile.msvc", "clean"], cwd=libpg_query_dir, check=False)
        else:
            subprocess.run(["make", "clean"], cwd=libpg_query_dir, check=False)
