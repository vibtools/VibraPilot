#!/usr/bin/env python3
"""Deterministic Windows x64 Nuitka OneDir + WiX MSI builder for VibraPilot."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import uuid
import venv
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from config.AppConfig.app import APP_NAME, VERSION

APP_VERSION = VERSION
TARGET_PYTHON = (3, 12)
NUITKA_VERSION = "4.1.3"
WIX_VERSION = "6.0.2"
WIX_UPGRADE_CODE = "5DB4BF6A-58D7-5A32-8FD4-2EA5AFABEBA2"
COMPONENT_NAMESPACE = uuid.UUID("9d0fda47-d850-50d5-b5e2-d10ad7a09a2f")
INSTALLER_REGISTRY_KEY = r"Software\Vib Tools\VibraPilot\InstallerComponents"

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WORK = ROOT / ".build"
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
BROWSER_DIR = ROOT / ".playwright-browsers"
REQ = ROOT / "requirements-build.txt"
WIX_SOURCE = ROOT / "installer" / "VibraPilot.wxs"
NUITKA_REPORT = WORK / "nuitka" / "VibraPilot-nuitka-report.xml"


class BuildError(RuntimeError):
    pass


def run(*args: str, env: dict[str, str] | None = None, cwd: Path = ROOT) -> None:
    command = [str(x) for x in args]
    print("$", subprocess.list2cmdline(command), flush=True)
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(command, cwd=cwd, env=merged, check=True)


def capture(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        [str(x) for x in args], cwd=cwd, check=True, capture_output=True, text=True
    )
    return (result.stdout or result.stderr).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def msi_product_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 4 or any(not part.isdigit() for part in parts):
        raise BuildError(f"VibraPilot version must be four numeric segments: {version}")
    major, minor, patch, revision = (int(part) for part in parts)
    mapped_build = patch * 100 + revision
    if not (0 <= major <= 255 and 0 <= minor <= 255 and 0 <= mapped_build <= 65535):
        raise BuildError(f"MSI version mapping is outside Windows Installer limits: {version}")
    return f"{major}.{minor}.{mapped_build}"


def validate_host() -> None:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() != "true":
        raise BuildError(
            "PR-12 package builds are authorized only in GitHub Actions. "
            "Download the GitHub Actions artifact for PC installation/acceptance testing."
        )
    if os.name != "nt" or platform.system().lower() != "windows":
        raise BuildError("PR-12 GitHub package build must run on Windows x64.")
    if struct.calcsize("P") * 8 != 64:
        raise BuildError("PR-12 GitHub package build requires 64-bit Python.")
    if sys.version_info[:2] != TARGET_PYTHON:
        raise BuildError("Run PR-12 GitHub packaging with CPython 3.12 x64.")


def clean() -> None:
    for path in (WORK, DIST, RELEASE, BROWSER_DIR):
        shutil.rmtree(path, ignore_errors=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    (WORK / "nuitka").mkdir(parents=True, exist_ok=True)
    (WORK / "wix").mkdir(parents=True, exist_ok=True)


def make_venv() -> Path:
    if VENV.exists():
        shutil.rmtree(VENV)
    venv.EnvBuilder(with_pip=True, clear=True).create(VENV)
    py = VENV / "Scripts" / "python.exe"
    run(str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQ))
    actual = capture(str(py), "-c", "import importlib.metadata as m; print(m.version('Nuitka'))")
    if actual != NUITKA_VERSION:
        raise BuildError(f"Nuitka version mismatch: expected {NUITKA_VERSION}, got {actual}")
    return py


def locate_wix() -> Path:
    explicit = os.environ.get("WIX_EXE", "").strip()
    candidate = Path(explicit).expanduser() if explicit else None
    if candidate and candidate.is_file():
        wix = candidate.resolve()
    else:
        found = shutil.which("wix") or shutil.which("wix.exe")
        if not found:
            raise BuildError(
                "WiX Toolset 6.0.2 was not found. Install/configure it manually or set WIX_EXE. "
                "The PR-12 builder never installs WiX or accepts WiX license/EULA terms automatically."
            )
        wix = Path(found).resolve()
    output = capture(str(wix), "--version")
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", output)
    actual = match.group(1) if match else output.strip()
    if actual != WIX_VERSION:
        raise BuildError(f"WiX version mismatch: expected {WIX_VERSION}, got {actual}")
    return wix


def validate_source(py: Path) -> None:
    run(str(py), "-m", "compileall", "-q", "src", "config/AppConfig", "vib_validation_app", "run.py")
    run(str(py), "scripts/verify_repository.py")


def install_browser(py: Path) -> None:
    env = {"PLAYWRIGHT_BROWSERS_PATH": str(BROWSER_DIR)}
    run(str(py), "-m", "playwright", "install", "chromium", env=env)
    if not BROWSER_DIR.is_dir() or not any(BROWSER_DIR.iterdir()):
        raise BuildError("Playwright Chromium fallback bundle was not provisioned.")


def _find_nuitka_dist(output_root: Path) -> Path:
    candidates = sorted(p for p in output_root.glob("*.dist") if p.is_dir())
    matches = [p for p in candidates if (p / f"{APP_NAME}.exe").is_file()]
    if len(matches) != 1:
        raise BuildError(
            f"Expected exactly one Nuitka standalone folder containing {APP_NAME}.exe; found {matches}"
        )
    return matches[0]


def build_app(py: Path) -> Path:
    output_root = WORK / "nuitka"
    icon_path = ROOT / "assets" / "icons" / "app.ico"
    args = [
        str(py), "-m", "nuitka",
        "--mode=standalone",
        "--enable-plugin=pyside6",
        "--mingw64",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        "--output-dir=" + str(output_root),
        "--output-filename=" + f"{APP_NAME}.exe",
        "--windows-icon-from-ico=" + str(icon_path),
        "--company-name=Vib Tools",
        "--product-name=" + APP_NAME,
        "--file-description=VibraPilot browser automation desktop application by Vib Tools.",
        "--file-version=" + APP_VERSION,
        "--product-version=" + APP_VERSION,
        "--copyright=Copyright (c) 2026 Vib Tools contributors",
        "--report=" + str(NUITKA_REPORT),
        "--include-data-dir=" + f"{ROOT / 'assets' / 'icons'}=assets/icons",
        "--include-data-dir=" + f"{ROOT / 'vib_validation_app' / 'assets' / 'icons'}=vib_validation_app/assets/icons",
        "--include-data-files=" + f"{ROOT / 'frozen_design_source' / 'CURRENT_FOUNDATION_TOKENS.json'}=frozen_design_source/CURRENT_FOUNDATION_TOKENS.json",
        "--include-data-files=" + f"{ROOT / 'config' / 'settings.defaults.json'}=config/settings.defaults.json",
        "--include-package=playwright",
        "--include-package-data=playwright",
        str(ROOT / "run.py"),
    ]
    run(*args)
    source_dist = _find_nuitka_dist(output_root)
    app_dir = DIST / APP_NAME
    shutil.copytree(source_dist, app_dir)
    shutil.copytree(BROWSER_DIR, app_dir / "ms-playwright", dirs_exist_ok=True)
    exe = app_dir / f"{APP_NAME}.exe"
    if not exe.is_file():
        raise BuildError(f"Expected executable not found: {exe}")
    for required in (
        app_dir / "config" / "settings.defaults.json",
        app_dir / "assets" / "icons" / "app.ico",
        app_dir / "frozen_design_source" / "CURRENT_FOUNDATION_TOKENS.json",
    ):
        if not required.is_file():
            raise BuildError(f"Required packaged resource is missing: {required}")
    if not (app_dir / "ms-playwright").is_dir():
        raise BuildError("Packaged Playwright Chromium fallback directory is missing.")
    return app_dir


def write_portable_manifest(release_dir: Path) -> Path:
    files = {}
    for p in sorted(release_dir.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.json":
            files[p.relative_to(release_dir).as_posix()] = sha256(p)
    manifest_path = release_dir / "SHA256SUMS.json"
    manifest_path.write_text(json.dumps(files, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def package_portable(app_dir: Path) -> tuple[Path, Path]:
    release_dir = RELEASE / f"{APP_NAME}-{APP_VERSION}-Windows-x64"
    shutil.copytree(app_dir, release_dir)
    write_portable_manifest(release_dir)
    zip_path = RELEASE / f"{release_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(release_dir.rglob("*")):
            if p.is_file():
                z.write(p, Path(release_dir.name) / p.relative_to(release_dir))
    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad:
            raise BuildError(f"ZIP CRC failure: {bad}")
    (RELEASE / f"{zip_path.name}.sha256").write_text(
        f"{sha256(zip_path)}  {zip_path.name}\n", encoding="ascii"
    )
    return release_dir, zip_path


def _wix_id(prefix: str, relative: str) -> str:
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _component_guid(relative: str) -> str:
    return "{" + str(uuid.uuid5(COMPONENT_NAMESPACE, relative.lower())).upper() + "}"


def generate_wix_file_fragment(payload_root: Path, destination: Path) -> Path:
    payload_root = payload_root.resolve()
    files = sorted(p for p in payload_root.rglob("*") if p.is_file())
    if not files:
        raise BuildError("MSI payload is empty.")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">',
        '  <Fragment>',
        '    <ComponentGroup Id="ApplicationFiles">',
    ]
    for file_path in files:
        rel = file_path.relative_to(payload_root).as_posix()
        rel_win = rel.replace("/", "\\")
        parent = Path(rel).parent.as_posix()
        cid = _wix_id("Cmp", rel)
        fid = _wix_id("Fil", rel)
        reg_name = _wix_id("cmp", rel)
        attrs = [f'Id="{cid}"', f'Guid="{_component_guid(rel)}"', 'Directory="INSTALLFOLDER"']
        if parent != ".":
            attrs.append(f'Subdirectory="{escape(parent.replace("/", "\\"))}"')
        lines.append("      <Component " + " ".join(attrs) + ">")
        lines.append(
            f'        <File Id="{fid}" Source="!(bindpath.PayloadRoot)\\{escape(rel_win)}" />'
        )
        lines.append(
            f'        <RegistryValue Root="HKCU" Key="{INSTALLER_REGISTRY_KEY}" '
            f'Name="{reg_name}" Type="integer" Value="1" KeyPath="yes" />'
        )
        lines.append("      </Component>")
    lines += [
        "    </ComponentGroup>",
        "  </Fragment>",
        "</Wix>",
        "",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return destination


def build_msi(wix: Path, release_dir: Path) -> Path:
    generated = generate_wix_file_fragment(release_dir, WORK / "wix" / "VibraPilot.Files.wxs")
    msi_path = RELEASE / f"{APP_NAME}-{APP_VERSION}-Windows-x64.msi"
    run(
        str(wix), "build",
        "-arch", "x64",
        "-d", f"MsiVersion={msi_product_version(APP_VERSION)}",
        "-b", f"PayloadRoot={release_dir}",
        "-intermediateFolder", str(WORK / "wix" / "obj"),
        "-o", str(msi_path),
        str(WIX_SOURCE),
        str(generated),
    )
    if not msi_path.is_file():
        raise BuildError(f"Expected MSI not found: {msi_path}")
    run(str(wix), "msi", "validate", str(msi_path))
    (RELEASE / f"{msi_path.name}.sha256").write_text(
        f"{sha256(msi_path)}  {msi_path.name}\n", encoding="ascii"
    )
    return msi_path


def write_build_manifest(release_dir: Path, zip_path: Path, msi_path: Path) -> Path:
    report_copy = RELEASE / f"{APP_NAME}-{APP_VERSION}-Nuitka-Report.xml"
    shutil.copy2(NUITKA_REPORT, report_copy)
    payload = {
        "schema_version": 1,
        "product": APP_NAME,
        "version": APP_VERSION,
        "windows_arch": "x64",
        "python": f"{TARGET_PYTHON[0]}.{TARGET_PYTHON[1]}",
        "compiler": {"name": "Nuitka", "version": NUITKA_VERSION, "mode": "standalone"},
        "installer": {
            "tool": "WiX Toolset",
            "version": WIX_VERSION,
            "scope": "perUser",
            "msi_product_version": msi_product_version(APP_VERSION),
            "upgrade_code": WIX_UPGRADE_CODE,
        },
        "build_provenance": {
            "provider": "github_actions",
            "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "sha": os.environ.get("GITHUB_SHA", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_number": os.environ.get("GITHUB_RUN_NUMBER", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
        },
        "browser_policy": {
            "google_chrome_preferred": True,
            "observable_chromium_fallback": True,
            "sandbox_default": False,
        },
        "browser_fallback": "bundled Playwright Chromium",
        "artifacts": {
            release_dir.name: {"type": "onedir", "files": sum(1 for p in release_dir.rglob('*') if p.is_file())},
            zip_path.name: {"sha256": sha256(zip_path)},
            msi_path.name: {"sha256": sha256(msi_path)},
            report_copy.name: {"sha256": sha256(report_copy)},
        },
        "data_safety": {
            "installer_tracks_packaged_files_only": True,
            "runtime_user_data_cleanup_authored": False,
        },
    }
    path = RELEASE / f"{APP_NAME}-{APP_VERSION}-Windows-x64-BUILD_MANIFEST.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    validate_host()
    clean()
    wix = locate_wix()
    py = make_venv()
    validate_source(py)
    install_browser(py)
    app_dir = build_app(py)
    release_dir, zip_path = package_portable(app_dir)
    msi_path = build_msi(wix, release_dir)
    manifest = write_build_manifest(release_dir, zip_path, msi_path)
    print("PR-12 PACKAGE BUILD: PASS")
    print(f"OneDir: {release_dir}")
    print(f"ZIP: {zip_path}")
    print(f"ZIP SHA-256: {sha256(zip_path)}")
    print(f"MSI: {msi_path}")
    print(f"MSI SHA-256: {sha256(msi_path)}")
    print(f"Manifest: {manifest}")
    print(f"Nuitka report: {RELEASE / f'{APP_NAME}-{APP_VERSION}-Nuitka-Report.xml'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, subprocess.CalledProcessError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
