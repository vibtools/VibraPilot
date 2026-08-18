from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_existing_chrome_secure_install_contract_remains_enforced():
    installer = (ROOT / "src/vibrapilot/chrome_installer.py").read_text(encoding="utf-8")
    runtime = (ROOT / "src/vibrapilot/chrome_runtime.py").read_text(encoding="utf-8")
    qt = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")

    for marker in (
        '"https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"',
        'GOOGLE_CHROME_EXPECTED_PUBLISHER = "Google LLC"',
        "inspect_windows_authenticode",
        'info.lpVerb = "runas"',
        "post_install_not_found",
    ):
        assert marker in installer
    assert 'channel"] = "chrome"' in backend
    assert 'channel"] = "chromium"' not in backend
    assert "discover_google_chrome" in runtime
    assert "def check_chrome_prerequisite_on_startup" in qt
    assert "self.app.ensure_chrome_ready(interactive=True)" in qt
