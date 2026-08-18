"""Secure Google Chrome prerequisite download/install orchestration for Windows.

VibraPilot never downloads or executes an installer without explicit UI consent.
The installer source is code-owned, HTTPS-only and restricted to Google's CDN.
A downloaded MSI is executed only after Windows Authenticode trust succeeds and
its signer identity is confirmed as Google LLC.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

import requests
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .chrome_runtime import ChromeRuntimeInfo, discover_google_chrome
from .windows_authenticode import (
    inspect_windows_authenticode,
    publisher_matches,
)

GOOGLE_CHROME_ENTERPRISE_MSI_URL = (
    "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"
)
GOOGLE_CHROME_INSTALLER_FILENAME = "googlechromestandaloneenterprise64.msi"
GOOGLE_CHROME_ALLOWED_DOWNLOAD_HOSTS = frozenset({"dl.google.com"})
GOOGLE_CHROME_EXPECTED_PUBLISHER = "Google LLC"
GOOGLE_CHROME_APPROVED_DOWNLOAD_PATH = "/dl/chrome/install/googlechromestandaloneenterprise64.msi"
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_ERROR_CANCELLED = 1223
_ERROR_INSTALL_USEREXIT = 1602
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
    if parsed.path != GOOGLE_CHROME_APPROVED_DOWNLOAD_PATH:
        raise ValueError("Google Chrome installer source path is not the exact approved Stable x64 MSI path.")
    return text


class _PolicyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        try:
            validate_download_url(newurl)
        except ValueError as exc:
            raise urllib.error.URLError(str(exc)) from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _RequestsDownloadResponse:
    """File-like HTTPS response backed by Requests' verified CA transport."""

    def __init__(self, session: requests.Session, response: requests.Response, final_url: str) -> None:
        self._session = session
        self._response = response
        self._final_url = final_url
        self.headers = response.headers
        self._response.raw.decode_content = True

    def read(self, size: int) -> bytes:
        return self._response.raw.read(size)

    def geturl(self) -> str:
        return self._final_url

    def close(self) -> None:
        try:
            self._response.close()
        finally:
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> bool:
        self.close()
        return False


def _default_open(url: str, *, timeout: float):
    """Open the approved Google MSI with verified TLS and redirect policy.

    Requests is already a runtime dependency and carries a bundled CA set, which
    avoids relying on the frozen executable's OpenSSL default-cert path. TLS
    verification stays mandatory and every redirect is revalidated against the
    exact Google host/path policy before another request is sent.
    """
    current_url = validate_download_url(url)
    session = requests.Session()
    headers = {
        "User-Agent": "VibraPilot Chrome Prerequisite Installer",
        "Accept-Encoding": "identity",
    }
    try:
        for _hop in range(6):
            response = session.get(
                current_url,
                headers=headers,
                stream=True,
                allow_redirects=False,
                timeout=timeout,
                verify=True,
            )
            if 300 <= int(response.status_code) < 400:
                location = str(response.headers.get("Location", "") or "").strip()
                response.close()
                if not location:
                    raise ChromeInstallError(
                        "download_redirect_rejected",
                        "Google Chrome installer download returned an invalid redirect.",
                        detail="Redirect response did not include a Location header.",
                    )
                redirected = urllib.parse.urljoin(current_url, location)
                try:
                    current_url = validate_download_url(redirected)
                except ValueError as exc:
                    raise ChromeInstallError(
                        "download_redirect_rejected",
                        "Google Chrome installer download redirected outside the approved Google source.",
                        detail=str(exc),
                    ) from exc
                continue
            response.raise_for_status()
            final_url = validate_download_url(str(response.url or current_url))
            return _RequestsDownloadResponse(session, response, final_url)
        raise ChromeInstallError(
            "download_redirect_rejected",
            "Google Chrome installer download exceeded the allowed redirect limit.",
        )
    except ChromeInstallError:
        session.close()
        raise
    except requests.RequestException as exc:
        session.close()
        raise ChromeInstallError(
            "download_failed",
            "Google Chrome installer could not be downloaded from the official Google source.",
            detail=str(exc),
        ) from exc
    except Exception:
        session.close()
        raise


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
    except (urllib.error.URLError, urllib.error.HTTPError, requests.RequestException, TimeoutError, OSError) as exc:
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


def verify_google_chrome_installer(path: str | Path) -> AuthenticodeResult:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file() or candidate.suffix.casefold() != ".msi":
        raise ChromeInstallError(
            "installer_invalid",
            "Downloaded Google Chrome installer is not a valid MSI file path.",
        )
    auth = inspect_windows_authenticode(candidate)
    if not auth.trusted:
        raise ChromeInstallError(
            "signature_invalid",
            "Google Chrome installer failed Windows Authenticode trust verification.",
            detail=auth.detail,
        )
    if not publisher_matches(auth.publisher, GOOGLE_CHROME_EXPECTED_PUBLISHER):
        raise ChromeInstallError(
            "wrong_publisher",
            "Google Chrome installer signer is not the required Google LLC publisher.",
            detail=auth.subject or auth.publisher or "Signer identity unavailable.",
        )
    return AuthenticodeResult(
        True, auth.publisher, auth.subject, auth.trust_status, auth.detail
    )


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


def _installer_execution_result(exit_code: int) -> InstallerExecutionResult:
    """Classify Windows Installer completion without conflating user cancellation."""
    code = int(exit_code)
    if code == _ERROR_INSTALL_USEREXIT:
        raise ChromeInstallError(
            "installer_cancelled",
            "Google Chrome installation was cancelled in Windows Installer.",
        )
    if code not in {0, _SUCCESS_REBOOT_INITIATED, _SUCCESS_REBOOT_REQUIRED}:
        raise ChromeInstallError(
            "installer_failed",
            f"Google Chrome installer failed with Windows Installer exit code {code}.",
        )
    return InstallerExecutionResult(
        code, code in {_SUCCESS_REBOOT_INITIATED, _SUCCESS_REBOOT_REQUIRED}
    )


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

    if code == _ERROR_INSTALL_USEREXIT:
        raise ChromeInstallError(
            "installer_cancelled",
            "Google Chrome installation was cancelled in Windows Installer.",
        )
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
