from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src" / "vibrapilot" / "qt_app.py"
WIDGETS_PATH = ROOT / "vib_validation_app" / "widgets.py"
STYLES_PATH = ROOT / "vib_validation_app" / "styles.py"
QT_TEXT = QT_PATH.read_text(encoding="utf-8")
WIDGETS_TEXT = WIDGETS_PATH.read_text(encoding="utf-8")
STYLES_TEXT = STYLES_PATH.read_text(encoding="utf-8")
QT_TREE = ast.parse(QT_TEXT, filename=str(QT_PATH))
WIDGETS_TREE = ast.parse(WIDGETS_TEXT, filename=str(WIDGETS_PATH))


def _method(name: str) -> ast.FunctionDef:
    cls = next(n for n in QT_TREE.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _method_source(name: str) -> str:
    return ast.get_source_segment(QT_TEXT, _method(name)) or ""


def _function_source(tree: ast.Module, text: str, name: str) -> str:
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(text, node) or ""


def test_page_header_description_is_optional_and_does_not_reserve_an_empty_description_row():
    source = _function_source(WIDGETS_TREE, WIDGETS_TEXT, "page_header")
    assert 'description: str = ""' in source
    assert "if description:" in source
    assert "desc.setMinimumHeight" not in source


def test_main_workspace_pages_do_not_render_decorative_page_subtitles():
    forbidden = (
        "Live overview of browser slots, automation progress, license state and next actions.",
        "Independent authorized Test Mode browser slots with file import, controls and live counters.",
        "Built-in and trusted local workflow plugins share the existing one-active-workflow control plane.",
        "Live processing records with search, status filtering and spreadsheet-safe export.",
        "Application, browser-worker, validation and automation events.",
        "Advanced Playwright controls for the managed Google Chrome runtime.",
        "Configure isolated global inputs for any installed workflow without activating it.",
        "Workflow-owned global configuration is isolated per installed workflow.",
        "Global safety, Task processing, interface and user-selected output locations.",
    )
    for text in forbidden:
        assert text not in QT_TEXT


def test_dashboard_metric_cards_have_no_decorative_helper_notes():
    source = _method_source("make_dashboard_page")
    for text in ("Independent sessions", "Active workflows", "Confirmed invites", "Failed records"):
        assert text not in source
    assert 'metric_card(name, value)' in source


def test_task_card_keeps_workflow_identity_in_state_but_not_as_visible_subtitle():
    task_cls = next(n for n in QT_TREE.body if isinstance(n, ast.ClassDef) and n.name == "TaskSlotWidget")
    build = next(n for n in task_cls.body if isinstance(n, ast.FunctionDef) and n.name == "_build")
    source = ast.get_source_segment(QT_TEXT, build) or ""
    assert 'f"Workflow: {workflow_name}"' not in source
    assert 'setObjectName("TaskSubtitle")' not in source
    task_source = ast.get_source_segment(QT_TEXT, task_cls) or ""
    assert "self.workflow_id" in task_source


def test_workflow_card_is_uniform_readable_metadata_tile_without_duplicate_active_action():
    source = _method_source("_workflow_card")
    assert "manifest.description" in source
    assert 'setObjectName("WorkflowDescription")' in source
    assert 'setObjectName("WorkflowCardTitle")' in source
    assert 'label("Workflow ID"' not in source
    assert 'button("Active", "secondary")' not in source
    assert "manifest.version" in source
    assert "workflow_origin" in source
    assert "_workflow_logo_path(manifest)" in source
    assert 'setMinimumWidth(280)' in source
    assert 'setMaximumWidth(360)' in source
    assert 'setFixedHeight(240)' in source
    assert 'QSizePolicy.Preferred, QSizePolicy.Fixed' in source
    assert 'setObjectName("WorkflowActionRow")' in source
    assert 'action_row.setFixedHeight(28)' in source
    assert 'lay.addWidget(action_row)' in source


def test_workflow_card_has_dedicated_subtle_two_pixel_tokenized_boundary():
    assert "QFrame#WorkflowCard {{" in STYLES_TEXT
    assert "background: {c['surface']};" in STYLES_TEXT
    assert "border: 2px solid {c['border']};" in STYLES_TEXT
    assert "border-radius: {radius}px;" in STYLES_TEXT


def test_workflow_showcase_uses_grid_reflow_and_preserves_activation_recovery_states():
    page = _method_source("make_workflows_page")
    refresh = _method_source("refresh_workflow_showcase")
    reflow = _method_source("_reflow_workflow_showcase")
    card_source = _method_source("_workflow_card")
    assert "QGridLayout" in page
    assert "self.workflow_showcase_cards" in page + refresh + reflow
    assert "columns = 1 if compact else (3 if wide else 2)" in reflow
    for marker in ("WorkflowActivateButton", "WorkflowRecoverButton", "WorkflowUnavailableButton"):
        assert marker in card_source


def test_workflow_input_and_settings_cards_drop_redundant_persistence_descriptions():
    inputs = _method_source("refresh_workflow_input_widgets")
    settings = _method_source("refresh_workflow_settings_widgets")
    assert "Values are stored only under workflow ID" not in inputs
    assert "Settings are isolated to workflow ID" not in settings
    assert 'card(schema.title)' in inputs
    assert 'card(schema.title)' in settings
    assert 'label("No additional settings", "Description", False)' in settings


def test_header_and_status_bar_drop_debug_or_redundant_chrome():
    shell = _method_source("_build_shell")
    responsive = _method_source("_apply_responsive_mode")
    navigate = _method_source("navigate")
    assert 'token_chip("Medium")' not in shell
    assert "responsive_badge" not in responsive
    assert "Vib Tools dark contract • Test Mode safety enforced" not in QT_TEXT
    assert 'showMessage(f"Viewing: {name}")' not in navigate
    assert 'token_chip("Licensed")' in shell


def test_security_and_runtime_evidence_copy_is_preserved():
    for required in (
        "Google Chrome Required",
        "Windows Authenticode",
        "Google LLC",
        "Browser automation is blocked until Google Chrome is available.",
        "Chrome Status",
        "Chrome Version",
        "Chrome Executable",
        "Sandbox: Enabled / Required",
        "Chromium Fallback: Disabled",
    ):
        assert required in QT_TEXT


def test_activation_keeps_functional_feedback_but_removes_decorative_subtitle_and_trust_footer():
    assert "Enter your license key to unlock" not in QT_TEXT
    assert "Secured by Licora Activation Engine" not in QT_TEXT
    assert 'setObjectName("ActivationStatus")' in QT_TEXT


def test_ui_polish_does_not_touch_frozen_behavior_markers():
    # Static safety anchors: the UI polish must not remove existing functional calls.
    for marker in (
        "self.request_workflow_switch(workflow_id)",
        "self.start_chrome_install",
        "self.save_workflow_inputs",
        "self.save_workflow_settings",
        "self.export_report_csv",
        "self.export_report_excel",
        "self.open_closed_tasks",
    ):
        assert marker in QT_TEXT
