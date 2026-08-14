"""Browser launch/runtime diagnostics for VibraPilot.

Observational only: this module does not change launch policy, fingerprint values,
profile ownership, network behavior, or workflow execution. Runtime evidence is
sanitized before it is written to the existing Logs root.
"""
from __future__ import annotations

import importlib.metadata
import json
import ntpath
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import which
from typing import Any

from .chrome_runtime import ChromeRuntimeInfo, discover_google_chrome

BROWSER_DIAGNOSTICS_SCHEMA_VERSION = 1
EXPECTED_PLAYWRIGHT_VERSION = "1.61.0"
_SENSITIVE_SWITCH_TOKENS = (
    "password", "passwd", "secret", "token", "cookie", "authorization",
    "auth-token", "api-key", "apikey", "private-key",
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def playwright_package_version() -> str:
    try:
        return importlib.metadata.version("playwright")
    except Exception:
        return "unknown"


def _redact_proxy_credentials(value: str) -> str:
    return re.sub(r"(://)[^/@\s:]+(?::[^/@\s]*)?@", r"\1<redacted>@", value)


def sanitize_command_argument(argument: str) -> str:
    text = str(argument)
    lower = text.lower()
    if any(token in lower for token in _SENSITIVE_SWITCH_TOKENS):
        if "=" in text:
            return f"{text.split('=', 1)[0]}=<redacted>"
        return "<redacted-sensitive-argument>"
    if lower.startswith("--proxy-server="):
        key, value = text.split("=", 1)
        return f"{key}={_redact_proxy_credentials(value)}"
    return text


def sanitize_command_line(command_line: str) -> str:
    text = str(command_line or "")
    if not text:
        return ""
    text = re.sub(
        r"(?i)(--(?:password|passwd|secret|token|cookie|authorization|auth-token|api-key|apikey|private-key)=)(\"[^\"]*\"|\S+)",
        lambda m: m.group(1) + "<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)(--proxy-server=)(\"[^\"]*\"|\S+)",
        lambda m: m.group(1) + _redact_proxy_credentials(m.group(2)),
        text,
    )
    return text


def sanitize_diagnostic_text(value: str) -> str:
    """Redact secret-bearing launch details while preserving forensic context."""
    text = sanitize_command_line(str(value or ""))
    text = re.sub(
        r"(?i)(\b(?:password|passwd|secret|token|authorization|auth-token|api-key|apikey|private-key)\b\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^,;\s}]+)",
        lambda m: m.group(1) + "<redacted>",
        text,
    )
    return _redact_proxy_credentials(text)


def _sanitize_json_value(value: Any) -> Any:
    """Keep diagnostic JSON types intact while sanitizing nested string values."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return sanitize_diagnostic_text(value) if isinstance(value, str) else value
    if isinstance(value, (list, tuple)):
        return [_sanitize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_json_value(item) for key, item in value.items()}
    return sanitize_diagnostic_text(str(value))


def sanitize_launch_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe, non-secret view of Playwright launch kwargs."""
    result: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key == "env":
            env = value if isinstance(value, dict) else {}
            result["env_override_keys"] = sorted(
                str(name) for name, env_value in env.items()
                if os.environ.get(str(name)) != str(env_value)
            )
            continue
        if key == "args" and isinstance(value, (list, tuple)):
            result[key] = [sanitize_command_argument(str(item)) for item in value]
            continue
        if key == "proxy" and isinstance(value, dict):
            result[key] = {
                "configured": bool(value.get("server")),
                "bypass_configured": bool(value.get("bypass")),
            }
            continue
        if key in {"storage_state", "http_credentials", "extra_http_headers"}:
            result[key] = "<configured>" if value else None
            continue
        result[key] = _sanitize_json_value(value)
    return result


def collect_page_environment(page: Any) -> dict[str, Any]:
    script = r"""
() => {
  const result = {
    user_agent: navigator.userAgent || null,
    platform: navigator.platform || null,
    webdriver: typeof navigator.webdriver === 'boolean' ? navigator.webdriver : null,
    language: navigator.language || null,
    languages: Array.from(navigator.languages || []),
    device_pixel_ratio: window.devicePixelRatio || null,
    viewport: {width: window.innerWidth, height: window.innerHeight},
    outer_window: {width: window.outerWidth, height: window.outerHeight},
    screen: {
      width: screen.width, height: screen.height,
      avail_width: screen.availWidth, avail_height: screen.availHeight,
      color_depth: screen.colorDepth, pixel_depth: screen.pixelDepth
    },
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
    hardware_concurrency: navigator.hardwareConcurrency || null,
    max_touch_points: navigator.maxTouchPoints || 0,
    user_agent_data: null,
    webgl: null,
    font_checks: {}
  };
  try {
    if (navigator.userAgentData) {
      result.user_agent_data = typeof navigator.userAgentData.toJSON === 'function'
        ? navigator.userAgentData.toJSON()
        : {brands: navigator.userAgentData.brands || null,
           mobile: navigator.userAgentData.mobile,
           platform: navigator.userAgentData.platform || null};
    }
  } catch (e) {}
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (gl) {
      const info = gl.getExtension('WEBGL_debug_renderer_info');
      result.webgl = {
        vendor: info ? gl.getParameter(info.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
        renderer: info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
      };
    }
  } catch (e) {}
  try {
    if (document.fonts && typeof document.fonts.check === 'function') {
      for (const font of ['Segoe UI', 'Arial', 'Times New Roman', 'Courier New'])
        result.font_checks[font] = document.fonts.check(`12px "${font}"`);
    }
  } catch (e) {}
  return result;
}
"""
    try:
        value = page.evaluate(script)
        return value if isinstance(value, dict) else {"status": "unexpected-result"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def collect_cdp_browser_metadata(context: Any, page: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    session = None
    try:
        session = context.new_cdp_session(page)
        version = session.send("Browser.getVersion")
        if isinstance(version, dict):
            result.update({
                "protocol_version": version.get("protocolVersion"),
                "product": version.get("product"),
                "revision": version.get("revision"),
                "user_agent": version.get("userAgent"),
                "javascript_version": version.get("jsVersion"),
            })
        try:
            command = session.send("Browser.getBrowserCommandLine")
            arguments = command.get("arguments") if isinstance(command, dict) else None
            if isinstance(arguments, list):
                result["browser_command_line_arguments"] = [
                    sanitize_command_argument(str(arg)) for arg in arguments
                ]
                result["browser_command_line_source"] = "cdp:Browser.getBrowserCommandLine"
        except Exception as exc:
            result["browser_command_line_cdp_status"] = "unavailable"
            result["browser_command_line_cdp_error"] = str(exc)
    except Exception as exc:
        result["status"] = "unavailable"
        result["error"] = str(exc)
    finally:
        if session is not None:
            try:
                session.detach()
            except Exception:
                pass
    return result


def collect_windows_browser_process(user_data_dir: str | Path | None) -> dict[str, Any]:
    """Find the browser process whose command line owns the managed profile."""
    if os.name != "nt":
        return {"status": "not_windows"}
    if not user_data_dir:
        return {"status": "no_profile_path"}
    powershell = which("pwsh") or which("powershell")
    if not powershell:
        return {"status": "powershell_unavailable"}
    target = str(Path(user_data_dir).expanduser().resolve())
    script = r"""
$target = $env:VIBRAPILOT_DIAG_PROFILE
$items = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine.IndexOf($target, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and
    ($_.Name -ieq 'chrome.exe' -or $_.Name -ieq 'chromium.exe')
} | Select-Object ProcessId, Name, ExecutablePath, CommandLine
if ($items) { $items | ConvertTo-Json -Compress } else { '[]' }
"""
    env = dict(os.environ)
    env["VIBRAPILOT_DIAG_PROFILE"] = target
    try:
        completed = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=8, check=False, env=env,
            creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
        )
    except Exception as exc:
        return {"status": "query_failed", "error": str(exc)}
    if completed.returncode != 0:
        return {"status": "query_failed", "error": completed.stderr.strip() or f"PowerShell exit {completed.returncode}"}
    try:
        parsed = json.loads(completed.stdout.strip() or "[]")
    except Exception as exc:
        return {"status": "parse_failed", "error": str(exc)}
    rows = parsed if isinstance(parsed, list) else [parsed]
    rows = [row for row in rows if isinstance(row, dict)]
    if not rows:
        return {"status": "not_found", "profile_path": target}
    browser_rows = [row for row in rows if "--type=" not in str(row.get("CommandLine") or "").lower()]
    primary = (browser_rows or rows)[0]
    return {
        "status": "found",
        "profile_path": target,
        "pid": primary.get("ProcessId"),
        "process_name": primary.get("Name"),
        "executable_path": primary.get("ExecutablePath"),
        "command_line": sanitize_command_line(str(primary.get("CommandLine") or "")),
        "matching_process_count": len(rows),
    }


def browser_runtime_policy_status(engine: str) -> str:
    """Classify measured browser identity against the Chrome-only policy."""
    value = str(engine or "")
    if value == "google_chrome":
        return "compliant"
    if value == "google_chrome_channel_unverified":
        return "unverified"
    return "violation"


def _windows_path_key(value: str | Path | None) -> str:
    text = str(value or "").strip().replace("/", "\\")
    return ntpath.normcase(ntpath.normpath(text)) if text else ""


def _classify_engine(
    *,
    requested_channel: str | None,
    requested_executable: str | None,
    fallback_used: bool,
    process: dict[str, Any],
    trusted_runtime: ChromeRuntimeInfo,
) -> tuple[str, str]:
    executable = str(process.get("executable_path") or "")
    actual_key = _windows_path_key(executable)
    trusted_key = _windows_path_key(trusted_runtime.executable_path)

    if actual_key:
        if trusted_runtime.available and trusted_key and actual_key == trusted_key:
            return "google_chrome", "confirmed_by_trusted_windows_process_path"
        normalized = actual_key.casefold()
        if "ms-playwright" in normalized:
            return "playwright_chromium", "confirmed_by_windows_process_path"
        if normalized.endswith(r"\google\chrome\application\chrome.exe"):
            return "untrusted_chrome_executable", "captured_process_path_not_equal_to_trusted_channel_target"
        return "unexpected_browser_executable", "captured_process_path_not_equal_to_trusted_channel_target"
    if fallback_used:
        return "playwright_chromium_fallback", "inferred_from_successful_fallback_path"
    if requested_executable:
        return "custom_chromium_executable", "inferred_from_requested_executable"
    if requested_channel == "chrome":
        return "google_chrome_channel_unverified", "requested_channel_without_process_path_evidence"
    if requested_channel == "chromium":
        return "playwright_chromium_channel", "inferred_from_successful_requested_channel"
    return "playwright_default_chromium", "inferred_from_launch_path"
def build_browser_diagnostics(*, slot_id: int, settings: dict[str, Any],
                              requested_launch_kwargs: dict[str, Any],
                              effective_launch_kwargs: dict[str, Any],
                              context: Any, page: Any,
                              user_data_dir: str | Path | None,
                              fallback_used: bool, fallback_reason: str,
                              persistent_context: bool) -> dict[str, Any]:
    requested_channel = requested_launch_kwargs.get("channel")
    requested_executable = requested_launch_kwargs.get("executable_path")
    process = collect_windows_browser_process(user_data_dir)
    trusted_runtime = discover_google_chrome()
    cdp = collect_cdp_browser_metadata(context, page)
    environment = collect_page_environment(page)
    engine, evidence = _classify_engine(
        requested_channel=str(requested_channel) if requested_channel else None,
        requested_executable=str(requested_executable) if requested_executable else None,
        fallback_used=bool(fallback_used),
        process=process,
        trusted_runtime=trusted_runtime,
    )
    command_line = str(process.get("command_line") or "")
    if not command_line and isinstance(cdp.get("browser_command_line_arguments"), list):
        command_line = " ".join(str(v) for v in cdp["browser_command_line_arguments"])
    profile = str(Path(user_data_dir).resolve()) if user_data_dir else None
    actual_playwright_version = playwright_package_version()
    playwright_version_matches = actual_playwright_version == EXPECTED_PLAYWRIGHT_VERSION
    return {
        "schema_version": BROWSER_DIAGNOSTICS_SCHEMA_VERSION,
        "captured_at": _now_iso(),
        "slot_id": int(slot_id),
        # Retained for compatibility with v1.0.6.18 evidence readers.
        "playwright_python_version": actual_playwright_version,
        "playwright": {
            "expected_version": EXPECTED_PLAYWRIGHT_VERSION,
            "actual_version": actual_playwright_version,
            "matches_expected": playwright_version_matches,
        },
        "requested": {
            "channel": requested_channel,
            "executable_path": requested_executable,
            "persistent_context": bool(persistent_context),
            "sandbox_enabled": bool(settings.get("sandbox_enabled", False)),
            "allow_chromium_fallback": bool(settings.get("allow_chromium_fallback", False)),
            "profile_path": profile,
            "profile_directory": str(settings.get("persistent_profile_directory", "") or ""),
            "http_cache_enabled": bool(settings.get("http_cache_enabled", True)),
            "viewport_width": settings.get("viewport_width"),
            "viewport_height": settings.get("viewport_height"),
            "device_scale_factor": settings.get("device_scale_factor"),
            "proxy_configured": bool(str(settings.get("proxy", "") or "").strip()),
            "dns_override_configured": bool(str(settings.get("dns_host_resolver_rules", "") or "").strip()),
            "custom_user_agent_configured": bool(str(settings.get("user_agent", "") or "").strip()),
        },
        "launch": {
            "requested_kwargs": sanitize_launch_kwargs(requested_launch_kwargs),
            "effective_kwargs": sanitize_launch_kwargs(effective_launch_kwargs),
            "fallback_used": bool(fallback_used),
            "fallback_reason": sanitize_diagnostic_text(str(fallback_reason or "")),
        },
        "actual": {
            "engine": engine,
            "engine_evidence": evidence,
            "product": cdp.get("product"),
            "protocol_version": cdp.get("protocol_version"),
            "javascript_version": cdp.get("javascript_version"),
            "executable_path": process.get("executable_path"),
            "trusted_chrome_executable": (
                str(trusted_runtime.executable_path)
                if trusted_runtime.executable_path else None
            ),
            "trusted_chrome_publisher": trusted_runtime.publisher or None,
            "trusted_chrome_signature": bool(trusted_runtime.signature_trusted),
            "pid": process.get("pid"),
            "profile_path": process.get("profile_path") or profile,
            "command_line": command_line or None,
            "process_evidence_status": process.get("status"),
            "cdp_command_line_status": cdp.get("browser_command_line_cdp_status", "captured" if cdp.get("browser_command_line_arguments") else "not_captured"),
        },
        "runtime_policy": {
            "name": "chrome_only_v1",
            "status": browser_runtime_policy_status(engine),
            "accepted_engines": ["google_chrome"],
            "sandbox_required": True,
            "chromium_fallback_allowed": False,
        },
        "browser_environment": environment,
        "cdp": cdp,
        "windows_process": process,
    }


def persist_browser_diagnostics(logs_dir: str | Path, slot_id: int,
                                record: dict[str, Any]) -> tuple[Path, Path]:
    root = Path(logs_dir) / "BrowserDiagnostics"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    timestamped = root / f"slot_{int(slot_id)}_{stamp}.json"
    latest = root / f"slot_{int(slot_id)}_latest.json"
    payload = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    for target in (timestamped, latest):
        temp = target.with_name(target.name + ".tmp")
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, target)
    return timestamped, latest


def browser_diagnostics_warnings(record: dict[str, Any]) -> list[str]:
    """Return non-fatal compatibility warnings derived from captured evidence."""
    warnings: list[str] = []
    playwright = record.get("playwright") if isinstance(record.get("playwright"), dict) else {}
    actual_version = str(
        playwright.get("actual_version")
        or record.get("playwright_python_version")
        or "unknown"
    )
    expected_version = str(playwright.get("expected_version") or EXPECTED_PLAYWRIGHT_VERSION)
    if actual_version != "unknown" and actual_version != expected_version:
        warnings.append(
            "Browser diagnostics dependency mismatch: "
            f"Playwright runtime={actual_version}, project-required={expected_version}. "
            "Reinstall the exact project dependencies before production acceptance."
        )
    actual = record.get("actual") if isinstance(record.get("actual"), dict) else {}
    engine = str(actual.get("engine") or "unknown")
    policy_status = browser_runtime_policy_status(engine)
    if policy_status == "violation":
        warnings.append(
            "Chrome-only runtime policy violation: "
            f"captured engine={engine}. VibraPilot requires the measured browser process "
            "to match the trusted Google Chrome channel executable."
        )
    elif policy_status == "unverified":
        warnings.append(
            "Chrome-only runtime identity is unverified: the Chrome channel was requested, "
            "but the Windows browser process executable path was not captured."
        )
    return warnings


def browser_diagnostics_summary(record: dict[str, Any]) -> str:
    actual = record.get("actual") if isinstance(record.get("actual"), dict) else {}
    requested = record.get("requested") if isinstance(record.get("requested"), dict) else {}
    launch = record.get("launch") if isinstance(record.get("launch"), dict) else {}
    playwright = record.get("playwright") if isinstance(record.get("playwright"), dict) else {}
    playwright_actual = str(
        playwright.get("actual_version")
        or record.get("playwright_python_version")
        or "unknown"
    )
    playwright_expected = str(playwright.get("expected_version") or EXPECTED_PLAYWRIGHT_VERSION)
    playwright_status = "match" if playwright_actual == playwright_expected else "mismatch"
    return (
        f"Browser diagnostics: engine={actual.get('engine', 'unknown')} "
        f"product={actual.get('product') or 'version unavailable'} "
        f"fallback={'yes' if launch.get('fallback_used') else 'no'} "
        f"sandbox={'on' if requested.get('sandbox_enabled') else 'off'} "
        f"playwright={playwright_actual}/{playwright_expected}:{playwright_status} "
        f"executable={actual.get('executable_path') or 'executable path not captured'} "
        f"profile={actual.get('profile_path') or requested.get('profile_path') or 'profile unavailable'}"
    )
