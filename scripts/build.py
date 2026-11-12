"""Build a native Windows one-file application with the active interpreter."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--console", action="store_true", help="Build with a debugging console")
    parser.add_argument("--dist-dir", type=Path, help="Alternative output folder when an older EXE is running")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Windows EXE sa musí zostaviť na Windows; cross-compilácia nie je podporovaná.")
    root = Path(__file__).resolve().parents[1]
    output_dir = args.dist_dir.resolve() if args.dist_dir is not None else root / "dist"
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--console" if args.console else "--windowed",
        "--name", "InstaGPhotoProcessor", "--noupx",
        "--distpath", str(output_dir),
        "--workpath", str(root / "build"),
        "--specpath", str(root / "build"),
        "--collect-all", "pillow_heif",
        "--collect-binaries", "imagecodecs",
        "--collect-data", "imagecodecs",
        "--copy-metadata", "imagecodecs",
        "--copy-metadata", "pillow_heif",
        "--hidden-import", "imagecodecs._shared",
        "--hidden-import", "imagecodecs._shared_cython",
        "--hidden-import", "imagecodecs._imcd",
        "--hidden-import", "imagecodecs._ultrahdr",
        "--hidden-import", "imagecodecs._cms",
        "--hidden-import", "imagecodecs._jpeg8",
        "--add-data", f"{root / 'insta_g' / 'assets'}{os.pathsep}insta_g/assets",
        "--add-data", f"{root / 'README-user.md'}{os.pathsep}.",
        "--add-data", f"{root / 'README-user-sk.md'}{os.pathsep}.",
        "--add-data", f"{root / 'README-user-cz.md'}{os.pathsep}.",
        "--hidden-import", "PIL.ImageCms",
        "--exclude-module", "tkinter",
        "--exclude-module", "pytest",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        str(root / "run_app.py"),
    ]
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = "0"
    result = subprocess.run(command, cwd=root, env=environment, check=False)
    if result.returncode:
        return result.returncode
    executable = output_dir / "InstaGPhotoProcessor.exe"
    if not executable.is_file():
        raise RuntimeError("PyInstaller skončil bez vytvorenia EXE.")
    print(f"Build hotový: {executable} ({executable.stat().st_size / 1024**2:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
