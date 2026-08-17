#!/usr/bin/env python3
"""Build the VibraPilot Windows x64 portable OneDir release with Nuitka."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for candidate in (SRC, ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from config.AppConfig.app import APP_NAME, VERSION

BUILD_ROOT = ROOT / ".build" / "portable-nuitka"
NUITKA_OUT = BUILD_ROOT / "nuitka"
RELEASE_ROOT = ROOT / "release"
TARGET_PYTHON = (3, 12)
TARGET_NUITKA = "4.1.3"
PORTABLE_NAME = f"{APP_NAME}-{VERSION}-Windows-x64-Portable"


class PortableBuildError(RuntimeError):
    pass


def run(*args: str, env: dict[str, str] | None = None, cwd: Path = ROOT) -> None:
    command = [str(arg) for arg in args]
    print("$", subprocess.list2cmdline(command), flush=True)
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(command, cwd=cwd, env=merged, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_host() -> None:
    if os.name != "nt" or platform.system().lower() != "windows":
        raise PortableBuildError("Portable release build must run on Windows.")
    if struct.calcsize("P") * 8 != 64:
        raise PortableBuildError("Portable release build must run from 64-bit Python.")
    if sys.version_info[:2] != TARGET_PYTHON:
        raise PortableBuildError(
            f"Portable release build requires Python {TARGET_PYTHON[0]}.{TARGET_PYTHON[1]} x64."
        )


def validate_toolchain() -> None:
    try:
        nuitka_version = importlib.metadata.version("Nuitka")
    except importlib.metadata.PackageNotFoundError as exc:
        raise PortableBuildError("Pinned Nuitka build dependency is not installed.") from exc
    if nuitka_version != TARGET_NUITKA:
        raise PortableBuildError(
            f"Nuitka version mismatch: expected {TARGET_NUITKA}, found {nuitka_version}."
        )
    playwright_version = importlib.metadata.version("playwright")
    if playwright_version != "1.61.0":
        raise PortableBuildError(
            f"Playwright version mismatch: expected 1.61.0, found {playwright_version}."
        )


def clean() -> None:
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    shutil.rmtree(RELEASE_ROOT, ignore_errors=True)
    NUITKA_OUT.mkdir(parents=True, exist_ok=True)
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)


def validate_source() -> None:
    run(sys.executable, "-m", "compileall", "-q", "src", "config/AppConfig", "vib_validation_app", "run.py")
    run(sys.executable, "scripts/verify_repository.py")


def build_nuitka() -> Path:
    icon_path = ROOT / "assets" / "icons" / "app.ico"
    env = {
        "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT))),
    }
    args = [
        sys.executable,
        "-m",
        "nuitka",
        "--mode=standalone",
        "--assume-yes-for-downloads",
        "--msvc=latest",
        "--enable-plugin=pyside6",
        "--playwright-include-browser=none",
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={icon_path}",
        f"--output-dir={NUITKA_OUT}",
        f"--output-filename={APP_NAME}.exe",
        f"--report={BUILD_ROOT / 'nuitka-compilation-report.xml'}",
        "--report-diffable",
        "--include-package=vibrapilot",
        "--include-package=vib_validation_app",
        "--include-package=config",
        "--include-package=playwright",
        "--include-package=openpyxl",
        "--include-package=xlrd",
        "--include-package=defusedxml",
        "--include-distribution-metadata=playwright",
        f"--include-data-dir={ROOT / 'assets' / 'icons'}=assets/icons",
        f"--include-data-dir={ROOT / 'vib_validation_app' / 'assets' / 'icons'}=vib_validation_app/assets/icons",
        f"--include-data-files={ROOT / 'config' / 'settings.defaults.json'}=config/settings.defaults.json",
        f"--include-data-files={ROOT / 'frozen_design_source' / 'CURRENT_FOUNDATION_TOKENS.json'}=frozen_design_source/CURRENT_FOUNDATION_TOKENS.json",
        str(ROOT / "run.py"),
    ]
    run(*args, env=env)

    candidates = [
        path
        for path in sorted(NUITKA_OUT.glob("*.dist"))
        if path.is_dir() and (path / f"{APP_NAME}.exe").is_file()
    ]
    if len(candidates) != 1:
        raise PortableBuildError(
            f"Expected exactly one Nuitka .dist directory containing {APP_NAME}.exe; found {candidates}."
        )
    return candidates[0]


def validate_compiled_runtime(dist_dir: Path) -> None:
    """Fail closed if Nuitka did not preserve the Playwright control driver."""
    required = (
        dist_dir / "playwright" / "driver" / "node.exe",
        dist_dir / "playwright" / "driver" / "package" / "cli.js",
    )
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise PortableBuildError(
            "Nuitka Playwright standalone support did not produce the required "
            f"control driver files: {missing}."
        )



def add_release_documents(dist_dir: Path) -> None:
    for name in ("LICENSE", "NOTICE"):
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, dist_dir / name)
    readme = dist_dir / "PORTABLE_README.txt"
    readme.write_text(
        f"{APP_NAME} {VERSION} — Windows x64 Portable\n"
        "\n"
        "This is a Nuitka standalone OneDir build. No installer is required.\n"
        "Extract the complete folder before running VibraPilot.exe.\n"
        "\n"
        "Google Chrome is an external prerequisite and is not bundled in this archive.\n"
        "The application uses its existing verified Google Chrome discovery/install flow.\n"
        "\n"
        "Do not move VibraPilot.exe out of this folder; the adjacent runtime files are required.\n",
        encoding="utf-8",
    )


def reject_forbidden_payload(dist_dir: Path) -> None:
    forbidden_dirs = {
        ".git",
        "project",
        "AppData",
        "Logs",
        "Reports",
        "FailedData",
        "BrowserProfiles",
        "__pycache__",
        ".pytest_cache",
        "ms-playwright",
        ".playwright-browsers",
    }
    forbidden_suffixes = {".msi", ".wixobj", ".wixpdb", ".wxs"}
    browser_binaries = {"chrome.exe", "chromium.exe", "headless_shell.exe"}
    for path in dist_dir.rglob("*"):
        rel_parts = set(path.relative_to(dist_dir).parts)
        if forbidden_dirs & rel_parts:
            raise PortableBuildError(f"Forbidden runtime/private directory packaged: {path}")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes:
            raise PortableBuildError(f"WiX/MSI payload is forbidden: {path}")
        if path.is_file() and path.name.lower() in browser_binaries:
            raise PortableBuildError(f"Bundled Chrome/Chromium browser binary is forbidden: {path}")


def build_info(dist_dir: Path) -> dict[str, object]:
    files = [path for path in dist_dir.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    largest = sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:20]
    return {
        "schema_version": 1,
        "app": APP_NAME,
        "version": VERSION,
        "platform": "Windows-x64",
        "format": "Nuitka-Standalone-OneDir",
        "nuitka_version": TARGET_NUITKA,
        "python": platform.python_version(),
        "source_commit": os.environ.get("GITHUB_SHA", "local"),
        "bundled_browser": False,
        "system_google_chrome_required": True,
        "wix_msi": False,
        "file_count_before_manifests": len(files),
        "uncompressed_bytes_before_manifests": total_bytes,
        "largest_files": [
            {
                "path": path.relative_to(dist_dir).as_posix(),
                "bytes": path.stat().st_size,
            }
            for path in largest
        ],
    }


def package(dist_dir: Path) -> tuple[Path, Path, Path]:
    release_dir = RELEASE_ROOT / PORTABLE_NAME
    shutil.copytree(dist_dir, release_dir)
    reject_forbidden_payload(release_dir)

    info_path = release_dir / "BUILD-INFO.json"
    info_path.write_text(json.dumps(build_info(release_dir), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest: dict[str, str] = {}
    for path in sorted(release_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            manifest[path.relative_to(release_dir).as_posix()] = sha256(path)
    (release_dir / "SHA256SUMS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    zip_path = RELEASE_ROOT / f"{PORTABLE_NAME}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(release_dir.rglob("*")):
            if path.is_file():
                archive.write(path, Path(release_dir.name) / path.relative_to(release_dir))
    with zipfile.ZipFile(zip_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise PortableBuildError(f"ZIP CRC verification failed: {bad_member}")

    digest = sha256(zip_path)
    sha_path = RELEASE_ROOT / f"{zip_path.name}.sha256"
    sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="ascii")
    report_copy = RELEASE_ROOT / f"{PORTABLE_NAME}-BUILD-INFO.json"
    shutil.copy2(release_dir / "BUILD-INFO.json", report_copy)

    print(f"Portable directory: {release_dir}")
    print(f"Portable ZIP: {zip_path}")
    print(f"SHA-256: {digest}")
    return release_dir, zip_path, sha_path


def main() -> int:
    validate_host()
    validate_toolchain()
    clean()
    validate_source()
    dist_dir = build_nuitka()
    validate_compiled_runtime(dist_dir)
    add_release_documents(dist_dir)
    package(dist_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PortableBuildError, subprocess.CalledProcessError) as exc:
        print(f"PORTABLE BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
