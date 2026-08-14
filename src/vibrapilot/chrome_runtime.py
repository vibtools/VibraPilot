"""Google Chrome runtime discovery for VibraPilot.

Phase 1 keeps Playwright as the automation layer while making the browser-engine
policy authoritative: only a genuine, system-installed Google Chrome runtime is
accepted. Download/install orchestration is intentionally deferred to Phase 2.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Callable, Iterable


@dataclass(frozen=True)
class ChromeRuntimeInfo:
    available: bool
    status: str
    executable_path: Path | None = None
    version: str = ""
    product_name: str = ""
    source: str = ""
    detail: str = ""


def _registry_candidates() -> list[tuple[str, Path]]:
    if os.name != "nt":
        return []
    try:
        import winreg  # type: ignore[attr-defined]
    except Exception:
        return []

    results: list[tuple[str, Path]] = []
    subkey = r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
    views = [0]
    for view_name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
        value = getattr(winreg, view_name, None)
        if isinstance(value, int) and value not in views:
            views.append(value)
    for hive_name in ("HKEY_CURRENT_USER", "HKEY_LOCAL_MACHINE"):
        hive = getattr(winreg, hive_name, None)
        if hive is None:
            continue
        for view in views:
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | view) as key:
                    value, _kind = winreg.QueryValueEx(key, None)
                text = str(value or "").strip().strip('"')
                if text:
                    results.append((f"registry:{hive_name}", Path(text)))
            except OSError:
                continue
    return results


def _filesystem_candidates(env: dict[str, str] | None = None) -> list[tuple[str, Path]]:
    environ = os.environ if env is None else env
    roots = (
        ("localappdata", environ.get("LOCALAPPDATA", "")),
        ("programfiles", environ.get("PROGRAMFILES", "")),
        ("programfiles_x86", environ.get("PROGRAMFILES(X86)", "")),
    )
    candidates: list[tuple[str, Path]] = []
    for source, raw_root in roots:
        root = str(raw_root or "").strip()
        if not root:
            continue
        candidates.append(
            (source, Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
        )
    return candidates


def google_chrome_candidates() -> list[tuple[str, Path]]:
    """Return de-duplicated Chrome candidates in discovery priority order."""
    output: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for source, path in [*_registry_candidates(), *_filesystem_candidates()]:
        key = os.path.normcase(str(Path(path).expanduser()))
        if key in seen:
            continue
        seen.add(key)
        output.append((source, Path(path).expanduser()))
    return output


def _windows_file_metadata(path: Path) -> tuple[str, str]:
    """Read Windows file ProductName/ProductVersion without new dependencies."""
    if os.name != "nt":
        return "", ""
    powershell = which("pwsh") or which("powershell")
    if not powershell:
        return "", ""
    script = r"""
$p = $env:VIBRAPILOT_CHROME_CANDIDATE
try {
  $v = (Get-Item -LiteralPath $p -ErrorAction Stop).VersionInfo
  @{ product = [string]$v.ProductName; version = [string]$v.ProductVersion } | ConvertTo-Json -Compress
} catch { exit 2 }
"""
    env = dict(os.environ)
    env["VIBRAPILOT_CHROME_CANDIDATE"] = str(path)
    try:
        completed = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            env=env,
            creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
        )
    except Exception:
        return "", ""
    if completed.returncode != 0:
        return "", ""
    try:
        payload = json.loads(completed.stdout.strip() or "{}")
    except Exception:
        return "", ""
    if not isinstance(payload, dict):
        return "", ""
    return (
        str(payload.get("product") or "").strip(),
        str(payload.get("version") or "").strip(),
    )


def validate_google_chrome_executable(path: str | Path, product_name: str = "") -> bool:
    """Return True only when the candidate can be identified as Google Chrome."""
    candidate = Path(path).expanduser()
    if not candidate.is_file() or candidate.name.lower() != "chrome.exe":
        return False
    product = str(product_name or "").strip().lower()
    # Fail closed when file metadata cannot establish branded-browser identity.
    # A canonical-looking path alone is not proof that chrome.exe is genuine.
    return bool(product) and "google chrome" in product


def discover_google_chrome(
    *,
    candidate_paths: Iterable[tuple[str, str | Path]] | None = None,
    metadata_reader: Callable[[Path], tuple[str, str]] | None = None,
    platform_name: str | None = None,
) -> ChromeRuntimeInfo:
    """Discover and validate an installed Google Chrome executable.

    Optional arguments provide deterministic test injection only; production
    callers use the platform defaults.
    """
    platform = os.name if platform_name is None else platform_name
    if platform != "nt" and candidate_paths is None:
        return ChromeRuntimeInfo(
            False,
            "unsupported_platform",
            detail="Google Chrome discovery is Windows-only.",
        )

    reader = _windows_file_metadata if metadata_reader is None else metadata_reader
    candidates = (
        google_chrome_candidates()
        if candidate_paths is None
        else [(str(source), Path(path).expanduser()) for source, path in candidate_paths]
    )
    rejected: list[str] = []
    for source, path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if not resolved.is_file():
            continue
        product_name, version = reader(resolved)
        if not validate_google_chrome_executable(resolved, product_name):
            rejected.append(str(resolved))
            continue
        return ChromeRuntimeInfo(
            True,
            "available",
            executable_path=resolved,
            version=version,
            product_name=product_name,
            source=source,
        )

    detail = ""
    if rejected:
        detail = "Rejected unverified/non-Google Chrome candidate(s): " + "; ".join(rejected)
    return ChromeRuntimeInfo(False, "not_found", detail=detail)
