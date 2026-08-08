#!/usr/bin/env python3
"""Static release verifier for VibraPilot Vib Tools desktop edition.

This verifier deliberately avoids importing PySide6 so it can run in lightweight
CI environments. It verifies the frozen Vib Tools design contract, backend API
parity against the preserved v1.0.6 source baseline, source-controlled licensing,
and key safety invariants.
"""
from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "vibrapilot"
BASELINE = ROOT / "project" / "research" / "source_baseline" / "VibraPilot_v1.0.6_original_app.py"

EXPECTED_BRAND_HASHES = {
    "vib_validation_app/tokens.py": "cdae402dccdb8e916f274ea5fa0b8ec1a6505fab6043462d35af8a93e1468a02",
    "vib_validation_app/styles.py": "83729e5b0e811e6b0cc4943dc729cbcf0cad92657eacbaebaacc0e0f56e3877b",
    "vib_validation_app/widgets.py": "5f13404bc98a053edb1ebd63760cd185632cbe84041594b7c4f5821043a3495d",
    "vib_validation_app/button_contract.py": "89bd33cbbfa00497a223e6ea5493e8aa4745d556e23447e28a0001c673381ce0",
    "vib_validation_app/focus_manager.py": "a47cf085635744f3bc7819a95f504e746a6cbe2be2143b8c8ef901bd4bb1a812",
    "frozen_design_source/CURRENT_FOUNDATION_TOKENS.json": "cbf1636b53a85c30dae839379653b6bbe0d0065e8f37cd919acaeb0c491e7616",
    "vib_validation_app/assets/icons/check.svg": "4aea38b95354030a63723f7e7f975e4d6a5b8a4f132a4bcda9a1a71a26c692e8",
    "vib_validation_app/assets/icons/chevron-down.svg": "d1a1f4bb388efe49cd5eff9d69361bdbac45d520e34ca4d11ed39b4256de87f6",
    "vib_validation_app/assets/icons/chevron-right.svg": "d27e0e90a22a13c5e8819cc6fef6336af4b610dc56446eb8199520bd36c2647c",
    "vib_validation_app/assets/icons/eye-off.svg": "e7b5de55df91771e85ab883f8ec317e952c1564903ccafb9d9722f2dd5061966",
    "vib_validation_app/assets/icons/eye.svg": "7619e35daa0f07351d52ca767a34ef83dc28b1ab854d9ce3bde7fa1531220316",
    "vib_validation_app/assets/icons/file.svg": "97cebfee4e4ba941551bbb8cee82091f1bc503f391382031804b65eae20f9d54",
    "vib_validation_app/assets/icons/folder.svg": "aecea0312a8cc0d2262a2a4eecd0341f53143259ea414db608d5372c432febd2",
    "vib_validation_app/assets/icons/minus.svg": "e09274e14616fe817b871cf923f05927e8b20b950d18f0bd0e208df1409d7747",
    "vib_validation_app/assets/icons/search.svg": "9df656e9653d7f14dec864af3d3b759e4fa105725dacbcab6c538f988c45b3ff",
}

CORE_CLASSES = [
    "SettingsManager", "LicenseManager", "TaskItem", "TaskState", "AutomationWorker",
    "SecurityChallenge", "SessionVerificationError", "TestModeRequired",
    "TestSendLimitReached", "SendClickOutcomeUncertain", "InviteRejected",
]


def fail(msg: str) -> None:
    raise SystemExit(f"VERIFY FAILED: {msg}")


def sha256(path: Path) -> str:
    """Return a cross-platform stable SHA-256 for frozen text contract files.

    Git may materialize LF-tracked text as CRLF on Windows when no explicit
    checkout policy is present. The frozen design contract is source-content
    based, so canonicalize CRLF to LF before hashing instead of treating the
    checkout platform as a design change.
    """
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def top_functions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def class_methods(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out[node.name] = [
                n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
    return out


def function_nodes(path: Path) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

def class_nodes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

def literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
    return None


print("[1/8] Python syntax")
for path in sorted(ROOT.rglob("*.py")):
    if any(part in {".venv", "build", "dist", "release", "__pycache__"} for part in path.parts):
        continue
    py_compile.compile(str(path), doraise=True)

print("[2/8] Exact Vib Tools frozen design-source hashes")
for rel, expected in EXPECTED_BRAND_HASHES.items():
    path = ROOT / rel
    if not path.is_file():
        fail(f"missing brand contract file: {rel}")
    actual = sha256(path)
    if actual != expected:
        fail(f"brand contract drift in {rel}: {actual} != {expected}")

print("[3/8] Frozen token values")
tokens = json.loads((ROOT / "frozen_design_source" / "CURRENT_FOUNDATION_TOKENS.json").read_text(encoding="utf-8"))
# Source-of-truth fields that identify the approved Vib Tools desktop contract.
checks = {
    ("theme", "mode"): "dark_only",
    ("theme", "font_family"): "Segoe UI Variable",
    ("theme", "fallback_font"): "Segoe UI",
    ("colors", "window_background"): "#090D14",
    ("colors", "surface"): "#111722",
    ("colors", "primary"): "#2563EB",
    ("colors", "secondary_accent"): "#38BDF8",
}
for keys, expected in checks.items():
    cur = tokens
    for key in keys:
        cur = cur[key]
    if cur != expected:
        fail(f"token {'.'.join(keys)} changed: {cur!r}")

print("[4/8] Core backend class/method parity")
if not BASELINE.is_file():
    fail("preserved v1.0.6 source baseline is missing")
original = class_methods(BASELINE)
production = class_methods(SRC / "backend.py")
original_nodes = class_nodes(BASELINE)
production_nodes = class_nodes(SRC / "backend.py")
allowed_settings_drift_classes = {"SettingsManager", "LicenseManager", "AutomationWorker"}
for cls in CORE_CLASSES:
    if cls not in original or cls not in production:
        fail(f"missing core class {cls}")
    if original[cls] != production[cls]:
        fail(f"backend method drift in {cls}: original={original[cls]} production={production[cls]}")
    if cls not in allowed_settings_drift_classes and ast.dump(original_nodes[cls], include_attributes=False) != ast.dump(production_nodes[cls], include_attributes=False):
        fail(f"backend implementation drift in core class {cls}")
if len(production.get("AutomationWorker", [])) != 54:
    fail("AutomationWorker must preserve all 54 v1.0.6 methods")
original_helpers = [name for name in top_functions(BASELINE) if name != "main"]
production_helpers = top_functions(SRC / "backend.py")
allowed_settings_helpers = {"_load_default_settings", "effective_ignored_default_args"}
if [name for name in production_helpers if name not in allowed_settings_helpers] != original_helpers:
    fail(f"top-level backend helper drift: original={original_helpers} production={production_helpers}")
original_function_nodes = function_nodes(BASELINE)
production_function_nodes = function_nodes(SRC / "backend.py")
for name in original_helpers:
    if name in {"validate_test_send_limit", "safe_test_send_limit"}:
        continue
    if ast.dump(original_function_nodes[name], include_attributes=False) != ast.dump(production_function_nodes[name], include_attributes=False):
        fail(f"backend helper implementation drift in {name}")

print("[5/8] Licensing and safety invariants")
backend_text = (SRC / "backend.py").read_text(encoding="utf-8")
qt_text = (SRC / "qt_app.py").read_text(encoding="utf-8")
if literal_assignment(SRC / "backend.py", "APP_VERSION") != "1.0.6.1":
    fail("APP_VERSION must be 1.0.6.1")
if literal_assignment(SRC / "__init__.py", "__version__") != "1.0.6.1":
    fail("package __version__ must be 1.0.6.1")
if literal_assignment(ROOT / "build.py", "APP_VERSION") != "1.0.6.1":
    fail("build APP_VERSION must be 1.0.6.1")
if 'version = "1.0.6.1"' not in (ROOT / "pyproject.toml").read_text(encoding="utf-8"):
    fail("pyproject version must be 1.0.6.1")
if 'version: 1.0.6.1' not in (ROOT / "CITATION.cff").read_text(encoding="utf-8"):
    fail("CITATION version must be 1.0.6.1")
if json.loads((ROOT / "vibproject.ygit").read_text(encoding="utf-8"))["project"]["version"] != "1.0.6.1":
    fail("vibproject version must be 1.0.6.1")
if json.loads((ROOT / "docs" / "docs.manifest.ygit").read_text(encoding="utf-8"))["documentation"]["version"] != "1.0.6.1":
    fail("documentation manifest version must be 1.0.6.1")
settings_defaults = json.loads((ROOT / "config" / "settings.defaults.json").read_text(encoding="utf-8"))
if settings_defaults.get("max_test_send_limit") != 50:
    fail("source-controlled default Test Send Limit must remain 50")
license_base = literal_assignment(SRC / "backend.py", "LICENSE_API_BASE_URL")
license_key = literal_assignment(SRC / "backend.py", "LICENSE_API_KEY")
if not isinstance(license_base, str) or not license_base.startswith("https://"):
    fail("license API base URL must remain source-controlled HTTPS")
if not isinstance(license_key, str) or not license_key.strip():
    fail("license API key must remain source-controlled and non-empty")
for marker in [
    '"X-API-Key"',
    '"Authorization"',
    'assert_test_mode',
    'SendClickOutcomeUncertain',
    'safe_spreadsheet_cell',
]:
    if marker not in backend_text:
        fail(f"required backend invariant marker missing: {marker}")
if "VIB_TOOLS_LICENSE_API_KEY" in backend_text or "os.environ.get(\"VIB_TOOLS_LICENSE_API_KEY\"" in backend_text:
    fail("environment/PowerShell API-key injection must not be present")

# Approved Settings-page/runtime scope.
for key in ("default_full_name", "default_number", "fallback_name", "update_click_count"):
    if settings_defaults.get(key) != "":
        fail(f"legacy contact default must be blank: {key}")
if 'DEFAULT_SETTINGS_FILE = ROOT_DIR / "config" / "settings.defaults.json"' not in backend_text:
    fail("settings defaults must be source-controlled outside Python literals")
if 'if parsed < 0:' not in backend_text:
    fail("Test Send Limit must accept Settings-controlled non-negative values")
if 'MAX_TEST_SEND_LIMIT' in backend_text:
    fail("Test Send Limit must not have a hardcoded upper ceiling in application code")

# Dedicated Browser Settings scope.
qt_tree_for_browser_settings = ast.parse(qt_text)
browser_groups_node = next(
    node
    for node in qt_tree_for_browser_settings.body
    if isinstance(node, ast.AnnAssign)
    and isinstance(node.target, ast.Name)
    and node.target.id == "BROWSER_SETTING_GROUPS"
)
browser_groups = ast.literal_eval(browser_groups_node.value)
browser_keys = {key for keys in browser_groups.values() for key in keys}
missing_browser_defaults = sorted(browser_keys - set(settings_defaults))
if missing_browser_defaults:
    fail(f"Browser Settings defaults missing: {missing_browser_defaults}")
worker_node_for_browser_settings = next(
    node
    for node in ast.parse(backend_text).body
    if isinstance(node, ast.ClassDef) and node.name == "AutomationWorker"
)
worker_source_for_browser_settings = ast.get_source_segment(
    backend_text, worker_node_for_browser_settings
) or ""
helper_node_for_browser_settings = next(
    node
    for node in ast.parse(backend_text).body
    if isinstance(node, ast.FunctionDef) and node.name == "effective_ignored_default_args"
)
helper_source_for_browser_settings = ast.get_source_segment(
    backend_text, helper_node_for_browser_settings
) or ""
runtime_browser_source = worker_source_for_browser_settings + helper_source_for_browser_settings
if len(browser_keys) != 147:
    fail(f"v1.0.6.1 Browser Settings control count drift: {len(browser_keys)} != 147")
missing_runtime_consumers = sorted(
    key
    for key in browser_keys
    if key != "browser_slot_default"
    and f'"{key}"' not in runtime_browser_source
)
if missing_runtime_consumers:
    fail(
        "Browser Settings controls without browser/runtime consumer: "
        f"{missing_runtime_consumers}"
    )
if '"browser_slot_default", DEFAULT_SETTINGS["browser_slot_default"]' not in qt_text:
    fail("Browser Slot Default must have a real workspace-initialization consumer")
for marker in [
    'def make_browser_settings_page(self) -> QWidget:',
    'def save_browser_settings(self) -> None:',
    'def reset_browser_settings(self) -> None:',
    '"Browser Settings": "search"',
]:
    if marker not in qt_text:
        fail(f"Browser Settings UI marker missing: {marker}")
for key in (
    "navigation_wait_until",
    "allow_chromium_fallback",
    "block_images",
    "preserve_storage_state_on_recycle",
    "use_persistent_context",
    "browser_executable_path",
    "record_har_enabled",
):
    if key not in browser_keys:
        fail(f"Browser Settings key missing from UI groups: {key}")
for marker in [
    "navigation_wait_until",
    "network_idle_timeout",
    "block_images",
    "allow_chromium_fallback",
    "preserve_storage_state_on_recycle",
    "scroll_before_interaction",
    "launch_persistent_context",
    "browser_executable_path",
    "persistent_user_data_dir",
    "device_scale_factor",
    "locale",
    "timezone_id",
    "permissions",
    "accept_downloads",
    "record_har_path",
    "additional_chromium_args",
    "auto_restart_browser_on_crash",
]:
    if marker not in backend_text:
        fail(f"Browser Settings runtime marker missing: {marker}")
if '"Network": ["request_timeout"' in qt_text or '"request_timeout": "Request / Network Timeout' in qt_text:
    fail("license/API request_timeout must not be exposed as a Playwright Browser Setting")
for fake_key in (
    "safe_browsing_enabled",
    "password_manager_enabled",
    "autofill_enabled",
    "screen_color_depth",
    "platform_spoof",
    "origin_trials_enabled",
    "hardware_acceleration_enabled",
    "disable_image_font_media_loading",
):
    if fake_key in browser_keys:
        fail(f"fake/legacy Browser Settings control must not be exposed: {fake_key}")
    if fake_key in settings_defaults:
        fail(f"fake/legacy Browser Settings default must not remain active: {fake_key}")
for forbidden_ui in (
    "Runtime Browser Contract (Informational)",
    "Chrome Policy / Profile-managed Features (Informational)",
):
    if forbidden_ui in qt_text:
        fail(f"read-only non-setting card must not appear in Browser Settings: {forbidden_ui}")
for marker in (
    "def effective_ignored_default_args(",
    '_PLAYWRIGHT_POPUP_BLOCKING_ARG = "--disable-popup-blocking"',
    '_PLAYWRIGHT_DISABLE_EXTENSIONS_ARG = "--disable-extensions"',
    '_PLAYWRIGHT_MUTE_AUDIO_ARG = "--mute-audio"',
    '"--disable-background-timer-throttling"',
    'extensions_enabled=extensions_enabled',
    'browser_args.append("--auto-open-devtools-for-tabs")',
    'launch_args["channel"] = "chromium"',
    'persistent_args.get("channel") == "chrome"',
):
    if marker not in backend_text:
        fail(f"Playwright/Chromium browser-authority marker missing: {marker}")
if 'if bool(settings.get("audio_enabled", DEFAULT_SETTINGS["audio_enabled"])):' not in helper_source_for_browser_settings:
    fail("Audio Enabled must override Playwright headless --mute-audio through ignored default args")
if '"devtools": bool(' in backend_text:
    fail("Playwright 1.61 removed launch(devtools=...); use the Chromium DevTools switch instead")
if 'elif name == "Browser Settings":' not in qt_text or qt_text.count("self.refresh_browser_settings_widgets()") < 3:
    fail("Browser Settings must refresh from SettingsManager on navigation, save and reset")
for marker in [
    '"App Settings": "settings"',
    '("App Settings", self.make_settings_page)',
    'worker.control_queue.put(("settings", {"settings": dict(self.settings.data)}))',
    'if command == "settings":',
]:
    if marker not in (qt_text + backend_text):
        fail(f"Browser/App Settings wiring marker missing: {marker}")

print("[6/8] Vib Tools UI integration contract")
for marker in [
    'app_qss("dark") + ActivationPage.activation_qss()',
    "apply_nav_button_contract",
    "install_keyboard_focus_ring",
    "CONST.sidebar_width",
    'NAV_SECTIONS = ["Dashboard", "Tasks", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]',
]:
    if marker not in qt_text:
        fail(f"required branded UI integration marker missing: {marker}")
if "customtkinter" in qt_text.lower() or "ctk." in qt_text:
    fail("new UI must not use the legacy CustomTkinter layer")
# Scope-locked v1.0.6 activation window contract.
activation_source = qt_text[qt_text.index("class ActivationPage(QWidget):"):qt_text.index("class TaskSlotWidget", qt_text.index("class ActivationPage(QWidget):"))]
activation_markers = [
    'WINDOW_BACKGROUND = "#0F172A"',
    'SURFACE = "#1E293B"',
    'BORDER = "#334155"',
    'PRIMARY = "#3B82F6"',
    'PRIMARY_HOVER = "#2563EB"',
    'TEXT_PRIMARY = "#F8FAFC"',
    'TEXT_SECONDARY = "#94A3B8"',
    'SUCCESS = "#10B981"',
    'root.setContentsMargins(40, 40, 40, 40)',
    'brand_icon = brand_icon_label(48, "VibraPilot")',
    'QLabel("VibraPilot Activation")',
    'QLabel("Enter your license key to unlock VibraPilot")',
    'QLabel("Email Address (Optional)")',
    'line_input("name@example.com"',
    'setPlaceholderText("VT-XXXX-XXXX-XXXX-XXXX")',
    'setFixedHeight(44)',
    'button("Activate License", "primary")',
    'QLabel("🔒 Secured by Licora Activation Engine")',
]
for marker in activation_markers:
    if marker not in activation_source:
        fail(f"activation-window contract marker missing: {marker}")
for forbidden in [
    "Validation:",
    "Activate / Login",
    "Vib Tools official desktop UI • Dark-first frozen design contract",
    'f"{DISPLAY_APP_NAME}  •  v{APP_VERSION}"',
]:
    if forbidden in activation_source:
        fail(f"legacy/debug activation-window marker still present: {forbidden}")
for marker in [
    "self.setFixedSize(460, 560)",
    "self._center_login_window()",
    "self.setMaximumSize(16777215, 16777215)",
    "self.setMinimumSize(CONST.min_window_width, CONST.min_window_height)",
]:
    if marker not in qt_text:
        fail(f"activation/workspace window-state marker missing: {marker}")

# Successful activation must transition exactly once into a live workspace.
transition_markers = [
    "self._transition_requested = False",
    "if self._transition_requested:",
    "self._transition_requested = True",
    "self._workspace_active = False",
    "self._workspace_transitioning = False",
    "if self._workspace_active or self._workspace_transitioning:",
    "self.setMinimumSize(0, 0)",
    "self.activation_page = None",
    "activation_page = self.activation_page",
    "if activation_page is not None and not self._workspace_active:",
]
for marker in transition_markers:
    if marker not in qt_text:
        fail(f"activation/workspace lifecycle marker missing: {marker}")

show_workspace_source = qt_text[qt_text.index("    def show_workspace(self) -> None:"):qt_text.index("    def _build_menu_bar", qt_text.index("    def show_workspace(self) -> None:"))]
if show_workspace_source.index("self._build_shell()") > show_workspace_source.index("self.setMinimumSize(CONST.min_window_width, CONST.min_window_height)"):
    fail("workspace minimum size must be restored only after the live shell is built")
if "tl = hbox(toolbar," in qt_text or "cl = hbox(controls," in qt_text:
    fail("workspace card must not receive a second top-level Qt layout")

# Central QSS remains the only direct style application in the application UI.
style_calls = len(re.findall(r"\.setStyleSheet\s*\(", qt_text))
if style_calls != 1:
    fail(f"expected exactly one central setStyleSheet call, found {style_calls}")

print("[7/8] Private-secret and source hygiene")
for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in {".git", ".venv", "build", "dist", "release", "__pycache__"} for part in path.parts):
        continue
    if path.suffix.lower() in {".zip", ".exe", ".ico", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    scan_text = text
    if path == SRC / "backend.py":
        # v1.0.6 private deployment intentionally source-controls one application
        # API key. Validate that contract in step 5, then remove only that assignment
        # from the generic secret scan so unrelated embedded credentials still fail.
        scan_text = re.sub(r'^LICENSE_API_KEY\s*=.*$', 'LICENSE_API_KEY = "SOURCE_CONTROLLED"', scan_text, flags=re.MULTILINE)
    if re.search(r"(?i)(?:api[_ -]?key|x-api-key)\s*[:=]\s*['\"](?!REPLACE_|YOUR_|example|demo|SOURCE_CONTROLLED)[A-Za-z0-9_-]{32,}['\"]", scan_text):
        fail(f"possible hard-coded real API key in {path.relative_to(ROOT)}")
for forbidden in ["includes/config.local.php", ".licora-encryption.key", ".env.production"]:
    if (ROOT / forbidden).exists():
        fail(f"private deployment artifact present: {forbidden}")


for marker in [
    'DISPLAY_APP_NAME = "VibraPilot"',
    'APP_NAME = "VibraPilot"',
    'QLabel("VibraPilot Activation")',
    'application.setWindowIcon(application_icon())',
    'self.setWindowIcon(application_icon())',
    'SetCurrentProcessExplicitAppUserModelID',
]:
    if marker not in (qt_text + backend_text):
        fail(f"VibraPilot branding/icon marker missing: {marker}")

print("[8/8] Required project files")
required = [
    "README.md", "CHANGELOG.md", "UPDATE_LOG.md", "VERSIONING.md", "LICENSE", "NOTICE", "pyproject.toml", "requirements.txt", "requirements-build.txt",
    "run.py", "build.py", "config/settings.defaults.json", "src/vibrapilot/backend.py", "src/vibrapilot/data_io.py",
    "src/vibrapilot/qt_app.py", "project/research/VIB_TOOLS_DESKTOP_UI_FORENSIC_AUDIT.md", "project/research/VIBRAPILOT_BASELINE_FREEZE.md",
    "project/specifications/FEATURE_PARITY_MATRIX.md", "docs/updates/v1.0.6.1.md", "docs/updates/v1.0.6.1-browser-settings-audit.md", "docs/updates/v1.0.6.1-vibrapilot-branding.md", "assets/icons/app.ico", "assets/icons/app.png", ".github/workflows/ci.yml",
]
for rel in required:
    if not (ROOT / rel).is_file():
        fail(f"required project file missing: {rel}")

print("Repository verification passed.")
