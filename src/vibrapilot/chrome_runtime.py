"""Trusted Google Chrome runtime discovery for VibraPilot.

VibraPilot launches Playwright's branded ``channel="chrome"``.  On Windows,
Playwright 1.61.0 resolves that channel from the first accessible Chrome path in
LOCALAPPDATA, Program Files, Program Files (x86), then HOMEDRIVE fallbacks.
Runtime preflight therefore validates exactly that same first existing target;
it never accepts a lower-priority or registry-only executable that Playwright
would not launch.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Callable, Iterable

from .windows_authenticode import (
    WindowsAuthenticodeInfo,
    inspect_windows_authenticode,
    publisher_matches,
)

GOOGLE_CHROME_EXPECTED_PUBLISHER = "Google LLC"
_CHROME_CHANNEL_SUFFIX = Path("Google") / "Chrome" / "Application" / "chrome.exe"


@dataclass(frozen=True)
class ChromeRuntimeInfo:
    available: bool
    status: str
    executable_path: Path | None = None
    version: str = ""
    product_name: str = ""
    source: str = ""
    detail: str = ""
    publisher: str = ""
    signature_trusted: bool = False


def _playwright_channel_candidates(
    env: dict[str, str] | None = None,
) -> list[tuple[str, Path]]:
    """Mirror Playwright 1.61.0's Windows ``chrome`` channel lookup order."""
    environ = os.environ if env is None else env
    raw_roots: list[tuple[str, str]] = [
        ("localappdata", str(environ.get("LOCALAPPDATA", "") or "")),
        ("programfiles", str(environ.get("PROGRAMFILES", "") or "")),
        ("programfiles_x86", str(environ.get("PROGRAMFILES(X86)", "") or "")),
    ]
    home_drive = str(environ.get("HOMEDRIVE", "") or "").strip()
    if home_drive:
        raw_roots.extend(
            [
                ("homedrive_programfiles", home_drive.rstrip("\\/") + r"\Program Files"),
                ("homedrive_programfiles_x86", home_drive.rstrip("\\/") + r"\Program Files (x86)"),
            ]
        )

    output: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for source, raw_root in raw_roots:
        root = raw_root.strip()
        if not root:
            continue
        path = Path(root).expanduser() / _CHROME_CHANNEL_SUFFIX
        key = os.path.normcase(os.path.normpath(str(path)))
        if key in seen:
            continue
        seen.add(key)
        output.append((source, path))
    return output


def google_chrome_candidates() -> list[tuple[str, Path]]:
    """Return candidates in the exact Playwright Chrome-channel priority order."""
    return _playwright_channel_candidates()


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


def validate_google_chrome_executable(
    path: str | Path,
    product_name: str = "",
    *,
    authenticode: WindowsAuthenticodeInfo | None = None,
) -> bool:
    """Accept only branded Google Chrome with trusted Google Authenticode identity."""
    candidate = Path(path).expanduser()
    if not candidate.is_file() or candidate.name.casefold() != "chrome.exe":
        return False
    product = str(product_name or "").strip().casefold()
    if not product or "google chrome" not in product:
        return False
    trust = authenticode if authenticode is not None else inspect_windows_authenticode(candidate)
    return bool(
        trust.trusted
        and publisher_matches(trust.publisher, GOOGLE_CHROME_EXPECTED_PUBLISHER)
    )


def discover_google_chrome(
    *,
    candidate_paths: Iterable[tuple[str, str | Path]] | None = None,
    metadata_reader: Callable[[Path], tuple[str, str]] | None = None,
    authenticode_reader: Callable[[Path], WindowsAuthenticodeInfo] | None = None,
    platform_name: str | None = None,
) -> ChromeRuntimeInfo:
    """Validate exactly the executable Playwright's Windows Chrome channel will use.

    ``candidate_paths`` is deterministic test injection. Production callers use
    the exact Playwright channel search order and stop at the first existing
    executable. If that target is not trusted Google Chrome, discovery fails
    closed instead of skipping to a lower-priority executable.
    """
    platform = os.name if platform_name is None else platform_name
    if platform != "nt" and candidate_paths is None:
        return ChromeRuntimeInfo(
            False,
            "unsupported_platform",
            detail="Google Chrome discovery is Windows-only.",
        )

    metadata = _windows_file_metadata if metadata_reader is None else metadata_reader
    trust_reader = inspect_windows_authenticode if authenticode_reader is None else authenticode_reader
    candidates = (
        google_chrome_candidates()
        if candidate_paths is None
        else [(str(source), Path(path).expanduser()) for source, path in candidate_paths]
    )

    for source, path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if not resolved.is_file():
            continue

        # Playwright returns the first accessible channel path. Do not skip an
        # invalid first target and "validate" another executable it would not launch.
        product_name, version = metadata(resolved)
        trust = trust_reader(resolved)
        if not validate_google_chrome_executable(
            resolved, product_name, authenticode=trust
        ):
            reasons: list[str] = []
            if "google chrome" not in str(product_name or "").casefold():
                reasons.append("ProductName does not identify Google Chrome")
            if not trust.trusted:
                reasons.append(trust.detail or "Windows Authenticode trust failed")
            elif not publisher_matches(trust.publisher, GOOGLE_CHROME_EXPECTED_PUBLISHER):
                reasons.append(
                    f"Authenticode publisher is {trust.publisher or 'unavailable'}, not {GOOGLE_CHROME_EXPECTED_PUBLISHER}"
                )
            return ChromeRuntimeInfo(
                False,
                "untrusted_channel_target",
                executable_path=resolved,
                version=version,
                product_name=product_name,
                source=source,
                detail="; ".join(reasons) or "Chrome channel target failed identity validation.",
                publisher=trust.publisher,
                signature_trusted=trust.trusted,
            )
        return ChromeRuntimeInfo(
            True,
            "available",
            executable_path=resolved,
            version=version,
            product_name=product_name,
            source=source,
            publisher=trust.publisher,
            signature_trusted=True,
        )

    return ChromeRuntimeInfo(
        False,
        "not_found",
        detail="Google Chrome was not found in Playwright's Windows chrome-channel locations.",
    )


class ChromeRuntimeRequiredError(RuntimeError):
    """Raised when Google Chrome is required but no trusted installation is available."""


def require_google_chrome() -> ChromeRuntimeInfo:
    """Return the trusted installed Google Chrome runtime or fail closed."""
    runtime = discover_google_chrome()
    if not runtime.available:
        detail = f" Detail: {runtime.detail}" if runtime.detail else ""
        raise ChromeRuntimeRequiredError(
            "Google Chrome is required for VibraPilot browser automation and no trusted Chrome channel target is available."
            + detail
        )
    return runtime
