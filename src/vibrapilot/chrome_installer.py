"""Secure Google Chrome prerequisite download/install orchestration for Windows.

VibraPilot never downloads or executes an installer without explicit UI consent.
The installer source is code-owned, HTTPS-only and restricted to Google's CDN.
A downloaded MSI is executed only after Windows Authenticode trust succeeds and
its signer identity is confirmed as Google LLC.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Callable

from .chrome_runtime import ChromeRuntimeInfo, discover_google_chrome

GOOGLE_CHROME_ENTERPRISE_MSI_URL = (
    "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"
)
GOOGLE_CHROME_INSTALLER_FILENAME = "googlechromestandaloneenterprise64.msi"
GOOGLE_CHROME_ALLOWED_DOWNLOAD_HOSTS = frozenset({"dl.google.com"})
GOOGLE_CHROME_EXPECTED_PUBLISHER = "Google LLC"
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_ERROR_CANCELLED = 1223
_SUCCESS_REBOOT_INITIATED = 1641
_SUCCESS_REBOOT_REQUIRED = 3010


class ChromeInstallError(RuntimeError):
    def __init__(self, code: str, message: str, *, detail: str = "") -> None:
        super().__init__(message)
        self.code = str(code)
        self.detail = str(detail)


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    sha256: str
    bytes_downloaded: int
    source_url: str


@dataclass(frozen=True)
class AuthenticodeResult:
    trusted: bool
    publisher: str
    subject: str
    trust_status: int
    detail: str = ""


@dataclass(frozen=True)
class InstallerExecutionResult:
    exit_code: int
    reboot_required: bool


@dataclass(frozen=True)
class ChromeInstallProgress:
    stage: str
    message: str
    current: int = 0
    total: int = 0


@dataclass(frozen=True)
class ChromeInstallResult:
    status: str
    runtime: ChromeRuntimeInfo
    sha256: str
    bytes_downloaded: int
    publisher: str
    installer_exit_code: int
    reboot_required: bool


def validate_download_url(url: str) -> str:
    text = str(url or "").strip()
    parsed = urllib.parse.urlsplit(text)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise ValueError("Google Chrome installer source must use HTTPS.")
    if hostname not in GOOGLE_CHROME_ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError("Google Chrome installer source host is not allowlisted.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Google Chrome installer source contains unsupported authority data.")
    if parsed.query or parsed.fragment:
        raise ValueError("Google Chrome installer source must not contain query or fragment data.")
    if not parsed.path.lower().endswith("/googlechromestandaloneenterprise64.msi"):
        raise ValueError("Google Chrome installer source path is not the approved Stable x64 MSI.")
    return text


class _PolicyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        try:
            validate_download_url(newurl)
        except ValueError as exc:
            raise urllib.error.URLError(str(exc)) from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _default_open(url: str, *, timeout: float):
    opener = urllib.request.build_opener(_PolicyRedirectHandler())
    request = urllib.request.Request(
        validate_download_url(url),
        headers={"User-Agent": "VibraPilot Chrome Prerequisite Installer"},
        method="GET",
    )
    return opener.open(request, timeout=timeout)


def _emit(
    callback: Callable[[ChromeInstallProgress], None] | None,
    stage: str,
    message: str,
    current: int = 0,
    total: int = 0,
) -> None:
    if callback is not None:
        callback(ChromeInstallProgress(stage, message, max(0, int(current)), max(0, int(total))))


def download_google_chrome_msi(
    destination_dir: str | Path,
    *,
    url: str = GOOGLE_CHROME_ENTERPRISE_MSI_URL,
    cancel_event: threading.Event | None = None,
    progress: Callable[[ChromeInstallProgress], None] | None = None,
    opener: Callable[..., object] | None = None,
    timeout: float = 60.0,
) -> DownloadResult:
    source_url = validate_download_url(url)
    destination = Path(destination_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    final_path = destination / GOOGLE_CHROME_INSTALLER_FILENAME
    partial_path = destination / (GOOGLE_CHROME_INSTALLER_FILENAME + ".part")
    final_path.unlink(missing_ok=True)
    partial_path.unlink(missing_ok=True)
    cancel = cancel_event or threading.Event()
    sha = hashlib.sha256()
    downloaded = 0
    total = 0
    _emit(progress, "downloading", "Downloading official Google Chrome installer…")
    open_call = _default_open if opener is None else opener
    try:
        with open_call(source_url, timeout=timeout) as response:
            final_url = validate_download_url(str(response.geturl()))
            try:
                total = max(0, int(response.headers.get("Content-Length", "0") or 0))
            except (TypeError, ValueError):
                total = 0
            with partial_path.open("wb") as handle:
                while True:
                    if cancel.is_set():
                        raise ChromeInstallError(
                            "cancelled", "Google Chrome installer download was cancelled."
                        )
                    chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    handle.write(chunk)
                    sha.update(chunk)
                    downloaded += len(chunk)
                    _emit(
                        progress,
                        "downloading",
                        "Downloading official Google Chrome installer…",
                        downloaded,
                        total,
                    )
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
            if cancel.is_set():
                raise ChromeInstallError(
                    "cancelled", "Google Chrome installer download was cancelled."
                )
            if downloaded <= 0:
                raise ChromeInstallError(
                    "download_empty", "Google Chrome installer download returned no data."
                )
            os.replace(partial_path, final_path)
            _emit(progress, "downloaded", "Google Chrome installer download completed.", downloaded, total)
            return DownloadResult(final_path, sha.hexdigest(), downloaded, final_url)
    except ChromeInstallError:
        partial_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        partial_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise ChromeInstallError(
            "download_failed",
            "Google Chrome installer could not be downloaded from the official Google source.",
            detail=str(exc),
        ) from exc
    except Exception as exc:
        partial_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise ChromeInstallError(
            "download_failed", "Google Chrome installer download failed.", detail=str(exc)
        ) from exc


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
    """Verify Authenticode trust with the Windows Software Publisher provider."""
    if os.name != "nt":
        return False, -1, "WinVerifyTrust is available only on Windows."
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        return False, -2, "Installer file does not exist."
    file_info = _WINTRUST_FILE_INFO(
        ctypes.sizeof(_WINTRUST_FILE_INFO), str(candidate), None, None
    )
    data = _WINTRUST_DATA()
    data.cbStruct = ctypes.sizeof(_WINTRUST_DATA)
    data.dwUIChoice = 2  # WTD_UI_NONE
    data.fdwRevocationChecks = 0  # WTD_REVOKE_NONE; OS provider policy remains authoritative.
    data.dwUnionChoice = 1  # WTD_CHOICE_FILE
    data.pFile = ctypes.pointer(file_info)
    data.dwStateAction = 1  # WTD_STATEACTION_VERIFY
    data.dwProvFlags = 0
    data.dwUIContext = 1  # WTD_UICONTEXT_INSTALL
    wintrust = ctypes.WinDLL("wintrust", use_last_error=True)
    verify = wintrust.WinVerifyTrust
    verify.argtypes = [wintypes.HWND, ctypes.POINTER(_GUID), ctypes.POINTER(_WINTRUST_DATA)]
    verify.restype = ctypes.c_long
    status = int(verify(None, ctypes.byref(_WINTRUST_ACTION_GENERIC_VERIFY_V2), ctypes.byref(data)))
    data.dwStateAction = 2  # WTD_STATEACTION_CLOSE
    try:
        verify(None, ctypes.byref(_WINTRUST_ACTION_GENERIC_VERIFY_V2), ctypes.byref(data))
    except Exception:
        pass
    return status == 0, status, "trusted" if status == 0 else f"WinVerifyTrust status {status}"


def read_authenticode_publisher(path: str | Path) -> tuple[str, str]:
    """Return the Authenticode signer simple name and subject using Windows PowerShell."""
    if os.name != "nt":
        return "", ""
    powershell = which("pwsh") or which("powershell")
    if not powershell:
        return "", ""
    candidate = Path(path).expanduser().resolve()
    script = r"""
$p = $env:VIBRAPILOT_CHROME_INSTALLER
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
    env["VIBRAPILOT_CHROME_INSTALLER"] = str(candidate)
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
    if not isinstance(payload, dict) or str(payload.get("status", "")).lower() != "valid":
        return "", str(payload.get("subject") or "") if isinstance(payload, dict) else ""
    return str(payload.get("publisher") or "").strip(), str(payload.get("subject") or "").strip()


def verify_google_chrome_installer(path: str | Path) -> AuthenticodeResult:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file() or candidate.suffix.lower() != ".msi":
        raise ChromeInstallError("installer_invalid", "Downloaded Google Chrome installer is not a valid MSI file path.")
    trusted, status, detail = winverifytrust_file(candidate)
    if not trusted:
        raise ChromeInstallError(
            "signature_invalid",
            "Google Chrome installer failed Windows Authenticode trust verification.",
            detail=detail,
        )
    publisher, subject = read_authenticode_publisher(candidate)
    if publisher.casefold() != GOOGLE_CHROME_EXPECTED_PUBLISHER.casefold():
        raise ChromeInstallError(
            "wrong_publisher",
            "Google Chrome installer signer is not the required Google LLC publisher.",
            detail=subject or publisher or "Signer identity unavailable.",
        )
    return AuthenticodeResult(True, publisher, subject, status, detail)


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", ctypes.c_uint32),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def run_google_chrome_installer(path: str | Path) -> InstallerExecutionResult:
    """Run the already-verified MSI through elevated Windows Installer and wait."""
    if os.name != "nt":
        raise ChromeInstallError("unsupported_platform", "Google Chrome prerequisite installation is Windows-only.")
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise ChromeInstallError("installer_missing", "Verified Google Chrome installer file is missing.")
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    msiexec = system_root / "System32" / "msiexec.exe"
    if not msiexec.is_file():
        raise ChromeInstallError("msiexec_missing", "Windows Installer executable could not be found.")

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    co_initialize = ole32.CoInitializeEx
    co_initialize.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    co_initialize.restype = ctypes.c_long
    co_uninitialize = ole32.CoUninitialize
    co_uninitialize.argtypes = []
    co_uninitialize.restype = None
    coinit_result = int(co_initialize(None, 0x2 | 0x4))  # STA + disable OLE1 DDE
    com_initialized = coinit_result in {0, 1}
    execute = shell32.ShellExecuteExW
    execute.argtypes = [ctypes.POINTER(_SHELLEXECUTEINFOW)]
    execute.restype = wintypes.BOOL
    wait_for_single_object = kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    wait_for_single_object.restype = wintypes.DWORD
    get_exit_code_process = kernel32.GetExitCodeProcess
    get_exit_code_process.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    get_exit_code_process.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    info = _SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(_SHELLEXECUTEINFOW)
    info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = str(msiexec)
    info.lpParameters = f'/i "{candidate}" /passive /norestart'
    info.lpDirectory = str(candidate.parent)
    info.nShow = 1  # SW_SHOWNORMAL

    if not execute(ctypes.byref(info)):
        error = int(ctypes.get_last_error())
        if com_initialized:
            co_uninitialize()
        if error == _ERROR_CANCELLED:
            raise ChromeInstallError("uac_cancelled", "Google Chrome installation was cancelled at the Windows UAC prompt.")
        if error == 5:
            raise ChromeInstallError("elevation_denied", "Windows denied permission to start the Google Chrome installer.")
        raise ChromeInstallError(
            "installer_start_failed",
            "Google Chrome installer could not be started with Windows elevation.",
            detail=f"Windows error {error}",
        )
    if not info.hProcess:
        if com_initialized:
            co_uninitialize()
        raise ChromeInstallError("installer_start_failed", "Windows did not return an installer process handle.")

    try:
        wait_result = int(wait_for_single_object(info.hProcess, 0xFFFFFFFF))
        if wait_result != 0:
            raise ChromeInstallError(
                "installer_wait_failed",
                "Waiting for the Google Chrome installer failed.",
                detail=f"WaitForSingleObject={wait_result}",
            )
        exit_code = wintypes.DWORD()
        if not get_exit_code_process(info.hProcess, ctypes.byref(exit_code)):
            error = int(ctypes.get_last_error())
            raise ChromeInstallError(
                "installer_exit_unknown",
                "Google Chrome installer exit status could not be read.",
                detail=f"Windows error {error}",
            )
        code = int(exit_code.value)
    finally:
        close_handle(info.hProcess)
        if com_initialized:
            co_uninitialize()

    if code not in {0, _SUCCESS_REBOOT_INITIATED, _SUCCESS_REBOOT_REQUIRED}:
        raise ChromeInstallError(
            "installer_failed",
            f"Google Chrome installer failed with Windows Installer exit code {code}.",
        )
    return InstallerExecutionResult(
        code, code in {_SUCCESS_REBOOT_INITIATED, _SUCCESS_REBOOT_REQUIRED}
    )


def install_google_chrome(
    *,
    cancel_event: threading.Event | None = None,
    progress: Callable[[ChromeInstallProgress], None] | None = None,
    temp_root: str | Path | None = None,
    downloader: Callable[..., DownloadResult] = download_google_chrome_msi,
    verifier: Callable[[Path], AuthenticodeResult] = verify_google_chrome_installer,
    runner: Callable[[Path], InstallerExecutionResult] = run_google_chrome_installer,
    discovery: Callable[[], ChromeRuntimeInfo] = discover_google_chrome,
) -> ChromeInstallResult:
    """Download, verify, elevate/install, and re-detect Google Chrome fail-closed."""
    cancel = cancel_event or threading.Event()
    cleanup_root = temp_root is None
    work_dir = (
        Path(tempfile.mkdtemp(prefix="VibraPilot-Chrome-"))
        if temp_root is None
        else Path(temp_root).expanduser().resolve()
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    download: DownloadResult | None = None
    try:
        download = downloader(
            work_dir,
            cancel_event=cancel,
            progress=progress,
        )
        if cancel.is_set():
            raise ChromeInstallError("cancelled", "Google Chrome installation was cancelled.")
        _emit(progress, "verifying", "Verifying Google Chrome installer authenticity…")
        auth = verifier(download.path)
        _emit(progress, "verified", f"Installer verified: {auth.publisher}.")
        if cancel.is_set():
            raise ChromeInstallError("cancelled", "Google Chrome installation was cancelled.")
        _emit(progress, "awaiting_uac", "Waiting for Windows administrator approval…")
        _emit(progress, "installing", "Installing Google Chrome…")
        execution = runner(download.path)
        _emit(progress, "rechecking", "Re-checking installed Google Chrome…")
        runtime = discovery()
        if not runtime.available:
            raise ChromeInstallError(
                "post_install_not_found",
                "Google Chrome installer completed, but a genuine installed Google Chrome runtime was not detected.",
                detail=runtime.detail,
            )
        _emit(progress, "completed", f"Google Chrome {runtime.version or ''} is ready.".strip())
        return ChromeInstallResult(
            "installed",
            runtime,
            download.sha256,
            download.bytes_downloaded,
            auth.publisher,
            execution.exit_code,
            execution.reboot_required,
        )
    finally:
        if cleanup_root:
            shutil.rmtree(work_dir, ignore_errors=True)
