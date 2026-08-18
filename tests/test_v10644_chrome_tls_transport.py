from __future__ import annotations

from pathlib import Path

import pytest


APPROVED = "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"


def test_v10644_default_transport_uses_requests_with_tls_verification_and_no_auto_redirect(monkeypatch):
    from src.vibrapilot import chrome_installer

    calls = []

    class Raw:
        decode_content = False
        def read(self, _size):
            return b""

    class Response:
        status_code = 200
        headers = {"Content-Length": "0"}
        raw = Raw()
        url = APPROVED
        def raise_for_status(self):
            return None
        def close(self):
            pass

    class Session:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()
        def close(self):
            pass

    monkeypatch.setattr(chrome_installer.requests, "Session", Session)
    with chrome_installer._default_open(APPROVED, timeout=12.5) as response:
        assert response.geturl() == APPROVED

    assert calls == [
        (
            APPROVED,
            {
                "headers": {
                    "User-Agent": "VibraPilot Chrome Prerequisite Installer",
                    "Accept-Encoding": "identity",
                },
                "stream": True,
                "allow_redirects": False,
                "timeout": 12.5,
                "verify": True,
            },
        )
    ]


def test_v10644_requests_transport_revalidates_every_redirect(monkeypatch):
    from src.vibrapilot import chrome_installer

    class Raw:
        decode_content = False
        def read(self, _size):
            return b""

    class Redirect:
        status_code = 302
        headers = {"Location": "https://evil.example/chrome.msi"}
        raw = Raw()
        url = APPROVED
        def close(self):
            pass

    class Session:
        def get(self, *_args, **_kwargs):
            return Redirect()
        def close(self):
            pass

    monkeypatch.setattr(chrome_installer.requests, "Session", Session)
    with pytest.raises(chrome_installer.ChromeInstallError) as exc:
        chrome_installer._default_open(APPROVED, timeout=10)
    assert exc.value.code == "download_redirect_rejected"


def test_v10644_tls_transport_keeps_authenticode_execution_gate_and_no_insecure_bypass():
    source = Path("src/vibrapilot/chrome_installer.py").read_text(encoding="utf-8")
    assert "verify=True" in source
    assert "allow_redirects=False" in source
    assert "verify=False" not in source
    assert "_create_unverified_context" not in source
    assert "CERT_NONE" not in source
    assert "verify_google_chrome_installer" in source
    assert "GOOGLE_CHROME_EXPECTED_PUBLISHER = \"Google LLC\"" in source
