"""Process-scoped system sleep protection for active VibraPilot automation.

The guard is intentionally narrow: on Windows it requests only
``PowerRequestSystemRequired`` while one or more Task workers are actually
processing. It never requests display power and never simulates user input.
Non-Windows verification hosts use a safe no-op backend.
"""
from __future__ import annotations

import atexit
import ctypes
import logging
import sys
import threading
from ctypes import wintypes
from typing import Protocol

_POWER_REQUEST_CONTEXT_VERSION = 0
_POWER_REQUEST_CONTEXT_SIMPLE_STRING = 0x00000001
_POWER_REQUEST_SYSTEM_REQUIRED = 0


class _PowerBackend(Protocol):
    def acquire(self) -> bool: ...
    def release(self) -> None: ...


class _NoOpPowerBackend:
    def acquire(self) -> bool:
        return True

    def release(self) -> None:
        return None


if sys.platform == "win32":
    class _ReasonContext(ctypes.Structure):
        _fields_ = [
            ("Version", wintypes.ULONG),
            ("Flags", wintypes.DWORD),
            ("SimpleReasonString", wintypes.LPWSTR),
        ]


class _WindowsPowerRequestBackend:
    """Own one native Windows Power Request handle."""

    def __init__(self, reason: str = "VibraPilot active automation") -> None:
        self.reason = str(reason)
        self.handle = None

    def acquire(self) -> bool:
        if self.handle:
            return True
        if sys.platform != "win32":
            return True
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        context = _ReasonContext(
            Version=_POWER_REQUEST_CONTEXT_VERSION,
            Flags=_POWER_REQUEST_CONTEXT_SIMPLE_STRING,
            SimpleReasonString=self.reason,
        )
        create = kernel32.PowerCreateRequest
        create.argtypes = [ctypes.POINTER(_ReasonContext)]
        create.restype = wintypes.HANDLE
        handle = create(ctypes.byref(context))
        if not handle or handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())

        set_request = kernel32.PowerSetRequest
        set_request.argtypes = [wintypes.HANDLE, ctypes.c_int]
        set_request.restype = wintypes.BOOL
        if not set_request(handle, _POWER_REQUEST_SYSTEM_REQUIRED):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(handle)
            raise ctypes.WinError(error)
        self.handle = handle
        return True

    def release(self) -> None:
        handle = self.handle
        if not handle:
            return
        self.handle = None
        if sys.platform != "win32":
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        clear_request = kernel32.PowerClearRequest
        clear_request.argtypes = [wintypes.HANDLE, ctypes.c_int]
        clear_request.restype = wintypes.BOOL
        try:
            if not clear_request(handle, _POWER_REQUEST_SYSTEM_REQUIRED):
                logging.warning(
                    "Windows system sleep power request could not be cleared: %s",
                    ctypes.WinError(ctypes.get_last_error()),
                )
        finally:
            kernel32.CloseHandle(handle)


def _default_backend() -> _PowerBackend:
    if sys.platform == "win32":
        return _WindowsPowerRequestBackend()
    return _NoOpPowerBackend()


class SystemSleepGuard:
    """Reference-count active Task owners around one process-level power request."""

    def __init__(self, *, backend: _PowerBackend | None = None) -> None:
        self._backend = backend if backend is not None else _default_backend()
        self._owners: set[str] = set()
        self._lock = threading.RLock()

    @property
    def owner_count(self) -> int:
        with self._lock:
            return len(self._owners)

    def acquire(self, owner: str) -> bool:
        token = str(owner).strip()
        if not token:
            raise ValueError("SystemSleepGuard owner token must not be empty")
        with self._lock:
            if token in self._owners:
                return True
            if not self._owners:
                try:
                    if not self._backend.acquire():
                        return False
                except Exception as exc:
                    logging.warning("Windows system sleep guard could not be acquired: %s", exc)
                    return False
            self._owners.add(token)
            return True

    def release(self, owner: str) -> None:
        token = str(owner).strip()
        if not token:
            return
        with self._lock:
            if token not in self._owners:
                return
            self._owners.remove(token)
            if self._owners:
                return
            try:
                self._backend.release()
            except Exception as exc:
                logging.warning("Windows system sleep guard could not be released cleanly: %s", exc)

    def release_all(self) -> None:
        with self._lock:
            if not self._owners:
                return
            self._owners.clear()
            try:
                self._backend.release()
            except Exception as exc:
                logging.warning("Windows system sleep guard cleanup failed: %s", exc)


SYSTEM_SLEEP_GUARD = SystemSleepGuard()
atexit.register(SYSTEM_SLEEP_GUARD.release_all)
