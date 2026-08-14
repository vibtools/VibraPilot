"""Windows Authenticode trust helpers used by Chrome runtime/install policy.

This module has no third-party dependencies.  It combines WinVerifyTrust's
Authenticode policy result with the signer certificate simple-name/subject so
callers can require both OS trust and an expected publisher identity.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from shutil import which


@dataclass(frozen=True)
class WindowsAuthenticodeInfo:
    trusted: bool
    publisher: str = ""
    subject: str = ""
    trust_status: int = -1
    detail: str = ""


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _WINTRUST_FILE_INFO(ctypes.Structure):
    _fields_ = [
        ("cbStruct", ctypes.c_uint32),
        ("pcwszFilePath", wintypes.LPCWSTR),
        ("hFile", wintypes.HANDLE),
        ("pgKnownSubject", ctypes.c_void_p),
    ]


class _WINTRUST_DATA(ctypes.Structure):
    _fields_ = [
        ("cbStruct", ctypes.c_uint32),
        ("pPolicyCallbackData", ctypes.c_void_p),
        ("pSIPClientData", ctypes.c_void_p),
        ("dwUIChoice", ctypes.c_uint32),
        ("fdwRevocationChecks", ctypes.c_uint32),
        ("dwUnionChoice", ctypes.c_uint32),
        ("pFile", ctypes.POINTER(_WINTRUST_FILE_INFO)),
        ("dwStateAction", ctypes.c_uint32),
        ("hWVTStateData", wintypes.HANDLE),
        ("pwszURLReference", wintypes.LPCWSTR),
        ("dwProvFlags", ctypes.c_uint32),
        ("dwUIContext", ctypes.c_uint32),
        ("pSignatureSettings", ctypes.c_void_p),
    ]


_WINTRUST_ACTION_GENERIC_VERIFY_V2 = _GUID(
    0x00AAC56B,
    0xCD44,
    0x11D0,
    (ctypes.c_ubyte * 8)(0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE),
)


def winverifytrust_file(path: str | Path) -> tuple[bool, int, str]:
    """Return Windows Authenticode policy trust for one file."""
    if os.name != "nt":
        return False, -1, "WinVerifyTrust is available only on Windows."
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        return False, -2, "File does not exist."

    file_info = _WINTRUST_FILE_INFO(
        ctypes.sizeof(_WINTRUST_FILE_INFO), str(candidate), None, None
    )
    data = _WINTRUST_DATA()
    data.cbStruct = ctypes.sizeof(_WINTRUST_DATA)
    data.dwUIChoice = 2  # WTD_UI_NONE
    data.fdwRevocationChecks = 0  # WTD_REVOKE_NONE
    data.dwUnionChoice = 1  # WTD_CHOICE_FILE
    data.pFile = ctypes.pointer(file_info)
    data.dwStateAction = 1  # WTD_STATEACTION_VERIFY
    data.dwProvFlags = 0
    data.dwUIContext = 1  # WTD_UICONTEXT_INSTALL

    try:
        wintrust = ctypes.WinDLL("wintrust", use_last_error=True)
        verify = wintrust.WinVerifyTrust
        verify.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(_GUID),
            ctypes.POINTER(_WINTRUST_DATA),
        ]
        verify.restype = ctypes.c_long
        status = int(
            verify(
                None,
                ctypes.byref(_WINTRUST_ACTION_GENERIC_VERIFY_V2),
                ctypes.byref(data),
            )
        )
        data.dwStateAction = 2  # WTD_STATEACTION_CLOSE
        try:
            verify(
                None,
                ctypes.byref(_WINTRUST_ACTION_GENERIC_VERIFY_V2),
                ctypes.byref(data),
            )
        except Exception:
            pass
    except Exception as exc:
        return False, -3, f"WinVerifyTrust invocation failed: {exc}"

    return status == 0, status, "trusted" if status == 0 else f"WinVerifyTrust status {status}"


def read_authenticode_publisher(path: str | Path) -> tuple[str, str]:
    """Return signer simple name and certificate subject for a valid signature."""
    if os.name != "nt":
        return "", ""
    powershell = which("pwsh") or which("powershell")
    if not powershell:
        return "", ""
    candidate = Path(path).expanduser().resolve()
    script = r"""
$p = $env:VIBRAPILOT_AUTHENTICODE_FILE
try {
  $sig = Get-AuthenticodeSignature -LiteralPath $p -ErrorAction Stop
  $cert = $sig.SignerCertificate
  if ($null -eq $cert) { exit 3 }
  @{
    status = [string]$sig.Status
    publisher = [string]$cert.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false)
    subject = [string]$cert.Subject
  } | ConvertTo-Json -Compress
} catch { exit 2 }
"""
    env = dict(os.environ)
    env["VIBRAPILOT_AUTHENTICODE_FILE"] = str(candidate)
    try:
        completed = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=20,
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
    if not isinstance(payload, dict) or str(payload.get("status", "")).casefold() != "valid":
        return "", str(payload.get("subject") or "") if isinstance(payload, dict) else ""
    return str(payload.get("publisher") or "").strip(), str(payload.get("subject") or "").strip()


def inspect_windows_authenticode(path: str | Path) -> WindowsAuthenticodeInfo:
    """Collect OS trust and signer identity without applying product policy."""
    trusted, status, detail = winverifytrust_file(path)
    if not trusted:
        return WindowsAuthenticodeInfo(False, trust_status=status, detail=detail)
    publisher, subject = read_authenticode_publisher(path)
    if not publisher:
        return WindowsAuthenticodeInfo(
            False,
            publisher="",
            subject=subject,
            trust_status=status,
            detail="Authenticode signer identity is unavailable.",
        )
    return WindowsAuthenticodeInfo(True, publisher, subject, status, detail)


def publisher_matches(publisher: str, expected_publisher: str) -> bool:
    """Apply one exact case-insensitive publisher policy."""
    return str(publisher or "").strip().casefold() == str(expected_publisher or "").strip().casefold()
