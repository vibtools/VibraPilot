from __future__ import annotations

from pathlib import Path

from vibrapilot.workflow import WorkflowManager, inspect_workflow_package, install_workflow_package
from _v10630_plugin_fixture import write_plugin_package


def test_unified_catalog_keeps_builtin_and_adds_valid_installed_plugin(tmp_path: Path):
    root = tmp_path / "Workflows"
    package = write_plugin_package(tmp_path / "invoice.vpworkflow")
    install_workflow_package(inspect_workflow_package(package), root, reserved_workflow_ids={"share_invite"})
    manager = WorkflowManager.with_available_workflows(workflow_root=root)
    assert [m.workflow_id for m in manager.list_workflows()] == ["invoice_fixture", "share_invite"]
    assert manager.workflow_origin("share_invite") == "builtin"
    assert manager.workflow_origin("invoice_fixture") == "plugin"
    assert manager.input_schema("invoice_fixture").workflow_id == "invoice_fixture"
    assert manager.settings_schema("invoice_fixture").workflow_id == "invoice_fixture"
    assert manager.task_schema("invoice_fixture").workflow_id == "invoice_fixture"


def test_broken_installed_plugin_is_issue_not_startup_crash(tmp_path: Path):
    root = tmp_path / "Workflows"
    broken = root / "broken"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{broken", encoding="utf-8")
    manager = WorkflowManager.with_available_workflows(workflow_root=root)
    assert [m.workflow_id for m in manager.list_workflows()] == ["share_invite"]
    assert manager.plugin_issues
    assert "broken" in manager.plugin_issues[0].path


def test_installed_plugin_runtime_resolves_through_standard_contract(tmp_path: Path):
    root = tmp_path / "Workflows"
    package = write_plugin_package(tmp_path / "invoice-runtime.vpworkflow")
    install_workflow_package(inspect_workflow_package(package), root, reserved_workflow_ids={"share_invite"})
    manager = WorkflowManager.with_available_workflows(
        workflow_root=root, active_workflow_id="invoice_fixture"
    )

    class Host:
        def set_workflow_step(self, value): self.step = value
        def set_workflow_metric(self, key, value): self.metric = (key, value)

    host = Host()
    runtime = manager.resolve_active_runtime(host)
    assert runtime.manifest.workflow_id == "invoice_fixture"
    assert runtime.session_ready(None) is True
    assert runtime.execute_item(object()) == "fixture-ok"
    assert host.step == "Creating invoice"
    assert host.metric == ("created", 1)
