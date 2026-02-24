"""Custom hatchling build hook that compiles libpg_query and bundles the shared library."""

from __future__ import annotations

import glob
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


class CustomBuildHook(BuildHookInterface):
    """Build hook that compiles libpg_query and includes it in the wheel."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Compile libpg_query and inject the shared library into the wheel.

        Set ``POSTGAST_SKIP_NATIVE_BUILD=1`` to skip compilation (useful in CI
        where the native library is built in a separate step).
        """
        if os.environ.get("POSTGAST_SKIP_NATIVE_BUILD"):
            self.app.display_warning("POSTGAST_SKIP_NATIVE_BUILD is set — skipping native library build.")
            return

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
            self._build_windows_dll(root, libpg_query_dir)
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

    def _build_windows_dll(self, root: Path, libpg_query_dir: Path) -> None:
        """Build a shared DLL on Windows using cl.exe and link.exe with the .def file.

        Upstream libpg_query's Makefile.msvc only produces a static .lib. This
        method compiles all sources and links them into a DLL using the project's
        pg_query_exports.def file.
        """
        self._ensure_msvc_env()

        def_file = root / "pg_query_exports.def"
        if not def_file.exists():
            msg = f"pg_query_exports.def not found at {def_file}"
            raise RuntimeError(msg)

        include_dirs = [
            libpg_query_dir,
            libpg_query_dir / "vendor",
            libpg_query_dir / "src" / "postgres" / "include",
            libpg_query_dir / "src" / "include",
            libpg_query_dir / "src" / "postgres" / "include" / "port" / "win32",
            libpg_query_dir / "src" / "postgres" / "include" / "port" / "win32_msvc",
        ]
        # Pass /I and path as separate list elements so subprocess quotes each
        # independently — safe when paths contain spaces.
        include_flags = [arg for d in include_dirs for arg in ("/I", str(d))]

        # Gather source files using the same globs as CI.

        src_files = (
            glob.glob(str(libpg_query_dir / "src" / "*.c"))
            + glob.glob(str(libpg_query_dir / "src" / "postgres" / "*.c"))
            + [str(libpg_query_dir / "vendor" / "protobuf-c" / "protobuf-c.c")]
            + [str(libpg_query_dir / "vendor" / "xxhash" / "xxhash.c")]
            + [str(libpg_query_dir / "protobuf" / "pg_query.pb-c.c")]
        )

        # Compile all sources to object files in a single output directory.
        obj_dir = libpg_query_dir / "obj"
        obj_dir.mkdir(exist_ok=True)
        compile_cmd = ["cl", *include_flags, "/c", f"/Fo{obj_dir}/", *src_files]
        subprocess.check_call(compile_cmd, cwd=libpg_query_dir)

        # Gather all .obj files and link into a DLL.
        obj_files = glob.glob(str(obj_dir / "*.obj"))
        link_cmd = ["link", "/DLL", f"/DEF:{def_file}", "/OUT:pg_query.dll", *obj_files]
        subprocess.check_call(link_cmd, cwd=libpg_query_dir)

    def _ensure_msvc_env(self) -> None:
        """Ensure MSVC tools (cl.exe, link.exe) are on PATH.

        If they're already available, this is a no-op. Otherwise, locates
        vcvarsall.bat via vswhere.exe and imports the developer environment
        variables into the current process.
        """
        if shutil.which("cl"):
            return

        vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
        if not vswhere.exists():
            msg = "cl.exe not on PATH and vswhere.exe not found — Visual Studio is required to build on Windows"
            raise RuntimeError(msg)

        result = subprocess.check_output(
            [str(vswhere), "-latest", "-property", "installationPath"],
            text=True,
        ).strip()
        if not result:
            msg = "vswhere did not return a Visual Studio installation path"
            raise RuntimeError(msg)

        vcvarsall = Path(result) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        if not vcvarsall.exists():
            msg = f"vcvarsall.bat not found at {vcvarsall}"
            raise RuntimeError(msg)

        # Run vcvarsall and capture the resulting environment.
        output = subprocess.check_output(
            f'call "{vcvarsall}" x64 >nul 2>&1 && set',
            shell=True,
            text=True,
        )
        for line in output.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ[key] = value

        if not shutil.which("cl"):
            msg = "cl.exe still not found after running vcvarsall.bat"
            raise RuntimeError(msg)

    def clean(self, versions: list[str]) -> None:
        """Remove compiled artifacts from the vendor directory."""
        root = Path(self.root)
        libpg_query_dir = root / "vendor" / "libpg_query"
        if libpg_query_dir.exists():
            subprocess.call(["make", "clean"], cwd=libpg_query_dir)
            obj_dir = libpg_query_dir / "obj"
            if obj_dir.exists():
                shutil.rmtree(obj_dir)
