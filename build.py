#!/usr/bin/env python3
"""Deterministic Windows x64 ONEDIR builder for the Vib Tools UI edition."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

from config.AppConfig.app import APP_NAME, VERSION

APP_VERSION = VERSION
TARGET_PYTHON = (3, 12)

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WORK = ROOT / ".build"
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
BROWSER_DIR = ROOT / ".playwright-browsers"
REQ = ROOT / "requirements-build.txt"


class BuildError(RuntimeError):
    pass


def run(*args: str, env: dict[str, str] | None = None, cwd: Path = ROOT) -> None:
    command = [str(x) for x in args]
    print("$", subprocess.list2cmdline(command), flush=True)
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(command, cwd=cwd, env=merged, check=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_host() -> None:
    if os.name != "nt" or platform.system().lower() != "windows":
        raise BuildError("Build must run on Windows.")
    if struct.calcsize("P") * 8 != 64:
        raise BuildError("Build must run from 64-bit Python.")
    if sys.version_info[:2] != TARGET_PYTHON:
        raise BuildError(f"Run this builder with Python {TARGET_PYTHON[0]}.{TARGET_PYTHON[1]} x64.")


def clean() -> None:
    for path in (WORK, DIST, RELEASE, BROWSER_DIR):
        shutil.rmtree(path, ignore_errors=True)
    RELEASE.mkdir(parents=True, exist_ok=True)


def make_venv() -> Path:
    if VENV.exists():
        shutil.rmtree(VENV)
    venv.EnvBuilder(with_pip=True, clear=True).create(VENV)
    py = VENV / "Scripts" / "python.exe"
    run(str(py), "-m", "pip", "install", "--upgrade", "pip")
    run(str(py), "-m", "pip", "install", "-r", str(REQ))
    return py


def validate_source(py: Path) -> None:
    run(str(py), "-m", "compileall", "-q", "src", "config/AppConfig", "vib_validation_app", "run.py")
    run(str(py), "scripts/verify_repository.py")


def install_browser(py: Path) -> None:
    env = {"PLAYWRIGHT_BROWSERS_PATH": str(BROWSER_DIR)}
    run(str(py), "-m", "playwright", "install", "chromium", env=env)


def build_app(py: Path) -> Path:
    icon_path = ROOT / "assets" / "icons" / "app.ico"
    args = [
        str(py), "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", APP_NAME,
        "--paths", str(ROOT / "src"),
        "--paths", str(ROOT),
        "--distpath", str(DIST),
        "--workpath", str(WORK / "pyinstaller"),
        "--specpath", str(WORK / "spec"),
        "--add-data", f"{ROOT / 'vib_validation_app' / 'assets' / 'icons'};vib_validation_app/assets/icons",
        "--add-data", f"{ROOT / 'assets' / 'icons'};assets/icons",
        "--add-data", f"{ROOT / 'frozen_design_source' / 'CURRENT_FOUNDATION_TOKENS.json'};frozen_design_source",
        "--add-data", f"{ROOT / 'config' / 'settings.defaults.json'};config",
        "--collect-all", "playwright",
        "--collect-all", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "xlrd",
        str(ROOT / "run.py"),
    ]
    if icon_path.exists():
        args[args.index(str(ROOT / "run.py")):args.index(str(ROOT / "run.py"))] = ["--icon", str(icon_path)]
    run(*args)
    app_dir = DIST / APP_NAME
    exe = app_dir / f"{APP_NAME}.exe"
    if not exe.exists():
        raise BuildError(f"Expected executable not found: {exe}")
    # backend.py preserves the original PyInstaller ROOT_DIR contract: sys._MEIPASS.
    # PyInstaller 6 ONEDIR maps that to the application _internal directory.
    internal_dir = app_dir / "_internal"
    internal_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BROWSER_DIR, internal_dir / "ms-playwright", dirs_exist_ok=True)
    return app_dir


def package(app_dir: Path) -> None:
    release_dir = RELEASE / f"{APP_NAME}-{APP_VERSION}-Windows-x64"
    shutil.copytree(app_dir, release_dir)
    manifest = {}
    for p in sorted(release_dir.rglob("*")):
        if p.is_file():
            manifest[p.relative_to(release_dir).as_posix()] = sha256(p)
    (release_dir / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    zip_path = RELEASE / f"{APP_NAME}-{APP_VERSION}-Windows-x64.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(release_dir.rglob("*")):
            if p.is_file():
                z.write(p, Path(release_dir.name) / p.relative_to(release_dir))
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad:
            raise BuildError(f"ZIP CRC failure: {bad}")
    digest = sha256(zip_path)
    (RELEASE / f"{zip_path.name}.sha256").write_text(f"{digest}  {zip_path.name}\n", encoding="ascii")
    print(f"Release: {zip_path}")
    print(f"SHA-256: {digest}")


def main() -> int:
    validate_host()
    clean()
    py = make_venv()
    validate_source(py)
    install_browser(py)
    app_dir = build_app(py)
    package(app_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, subprocess.CalledProcessError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
