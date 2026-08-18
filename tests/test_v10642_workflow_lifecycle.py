from __future__ import annotations

import json
from pathlib import Path

import pytest

from _v10630_plugin_fixture import plugin_payload, write_plugin_package


def _versioned_package(path: Path, workflow_id: str, version: str) -> Path:
    manifest = dict(plugin_payload(workflow_id)["manifest.json"])
    manifest["version"] = version
    return write_plugin_package(path, workflow_id, mutate={"manifest.json": manifest})


def test_numeric_workflow_version_comparison_is_strict_and_not_lexicographic():
    from vibrapilot.workflow import compare_workflow_versions

    assert compare_workflow_versions("1.0.9", "1.0.10") < 0
    assert compare_workflow_versions("1.0.10", "1.0.9") > 0
    assert compare_workflow_versions("1.2", "1.2.0") == 0
    assert compare_workflow_versions("2", "1.99.99") > 0


def test_update_workflow_package_requires_strictly_newer_version_and_replaces_atomically(tmp_path: Path):
    from vibrapilot.workflow import (
        inspect_workflow_package,
        install_workflow_package,
        update_workflow_package,
        WorkflowManager,
    )

    root = tmp_path / "Workflows"
    v1 = _versioned_package(tmp_path / "v1.vpworkflow", "invoice_fixture", "1.0.0")
    install_workflow_package(inspect_workflow_package(v1), root, reserved_workflow_ids=set())

    same = _versioned_package(tmp_path / "same.vpworkflow", "invoice_fixture", "1.0.0")
    with pytest.raises(Exception, match="strictly newer"):
        update_workflow_package(inspect_workflow_package(same), root, reserved_workflow_ids=set())

    lower = _versioned_package(tmp_path / "lower.vpworkflow", "invoice_fixture", "0.9.9")
    with pytest.raises(Exception, match="strictly newer"):
        update_workflow_package(inspect_workflow_package(lower), root, reserved_workflow_ids=set())

    v2 = _versioned_package(tmp_path / "v2.vpworkflow", "invoice_fixture", "1.1.0")
    updated = update_workflow_package(inspect_workflow_package(v2), root, reserved_workflow_ids=set())
    assert updated.manifest.version == "1.1.0"
    assert WorkflowManager.with_available_workflows(workflow_root=root).require_workflow("invoice_fixture").version == "1.1.0"
    metadata = json.loads((root / "invoice_fixture" / ".vibrapilot-plugin.json").read_text(encoding="utf-8"))
    assert metadata["package_sha256"] == inspect_workflow_package(v2).package_sha256
    assert not list(root.glob(".lifecycle-*"))


def test_update_rolls_back_old_workflow_if_post_swap_validation_fails(monkeypatch, tmp_path: Path):
    from vibrapilot.workflow import inspect_workflow_package, install_workflow_package
    from vibrapilot.workflow import plugin_loader

    root = tmp_path / "Workflows"
    old_package = _versioned_package(tmp_path / "old.vpworkflow", "invoice_fixture", "1.0.0")
    install_workflow_package(inspect_workflow_package(old_package), root, reserved_workflow_ids=set())
    old_manifest_bytes = (root / "invoice_fixture" / "manifest.json").read_bytes()

    new_package = _versioned_package(tmp_path / "new.vpworkflow", "invoice_fixture", "1.1.0")
    inspection = inspect_workflow_package(new_package)
    real_load = plugin_loader.load_workflow_directory
    calls = {"destination": 0}

    def fail_only_after_swap(path: Path):
        path = Path(path)
        if path.resolve() == (root / "invoice_fixture").resolve():
            calls["destination"] += 1
            if calls["destination"] == 1:
                raise plugin_loader.WorkflowPluginValidationError("synthetic post-swap validation failure")
        return real_load(path)

    monkeypatch.setattr(plugin_loader, "load_workflow_directory", fail_only_after_swap)
    with pytest.raises(Exception, match="post-swap"):
        plugin_loader.update_workflow_package(inspection, root, reserved_workflow_ids=set())

    assert (root / "invoice_fixture" / "manifest.json").read_bytes() == old_manifest_bytes
    assert real_load(root / "invoice_fixture").manifest.version == "1.0.0"


def test_remove_installed_workflow_removes_only_executable_package_directory(tmp_path: Path):
    from vibrapilot.workflow import inspect_workflow_package, install_workflow_package, remove_installed_workflow

    root = tmp_path / "Workflows"
    package = _versioned_package(tmp_path / "one.vpworkflow", "invoice_fixture", "1.0.0")
    install_workflow_package(inspect_workflow_package(package), root, reserved_workflow_ids=set())
    unrelated = tmp_path / "workflow_inputs.json"
    unrelated.write_text('{"preserve": true}', encoding="utf-8")

    removed = remove_installed_workflow("invoice_fixture", root)
    assert removed.workflow_id == "invoice_fixture"
    assert not (root / "invoice_fixture").exists()
    assert unrelated.read_text(encoding="utf-8") == '{"preserve": true}'


def test_prepared_update_transaction_recovers_previous_workflow_after_interrupted_swap(tmp_path: Path):
    import os
    import shutil

    from vibrapilot.workflow import (
        inspect_workflow_package,
        install_workflow_package,
        load_workflow_directory,
        recover_workflow_lifecycle_transactions,
    )

    root = tmp_path / "Workflows"
    old_package = _versioned_package(tmp_path / "old-recovery.vpworkflow", "invoice_fixture", "1.0.0")
    new_package = _versioned_package(tmp_path / "new-recovery.vpworkflow", "invoice_fixture", "1.1.0")
    install_workflow_package(inspect_workflow_package(old_package), root, reserved_workflow_ids=set())

    tx = root / ".transactions" / "invoice_fixture-update-synthetic"
    tx.mkdir(parents=True)
    backup = tx / "backup"
    os.replace(root / "invoice_fixture", backup)

    # Model an interrupted update after a replacement directory became visible but
    # before COMMITTED was persisted. Recovery must prefer the backed-up old package.
    staged_root = tmp_path / "new-visible"
    staged_root.mkdir()
    new_inspection = inspect_workflow_package(new_package)
    with __import__("zipfile").ZipFile(new_package) as archive:
        archive.extractall(staged_root)
    # The test fixture package is rooted directly at archive root; add install metadata
    # by copying from a normally installed temporary instance so directory validation is exact.
    temp_install_root = tmp_path / "temp-install"
    install_workflow_package(new_inspection, temp_install_root, reserved_workflow_ids=set())
    shutil.rmtree(staged_root)
    os.replace(temp_install_root / "invoice_fixture", root / "invoice_fixture")

    (tx / "transaction.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "PREPARED",
                "action": "update",
                "workflow_id": "invoice_fixture",
                "target_version": "1.1.0",
                "created_at": "2026-08-18T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    actions = recover_workflow_lifecycle_transactions(root)
    assert actions == ["rolled back update transaction for invoice_fixture"]
    assert load_workflow_directory(root / "invoice_fixture").manifest.version == "1.0.0"
    assert not (root / ".transactions").exists()


def test_default_workflow_can_be_deactivated_without_mutating_task_state(tmp_path: Path):
    from vibrapilot.workflow import WorkflowManager, WorkflowStateStore, inspect_workflow_package, install_workflow_package

    root = tmp_path / "Workflows"
    package = _versioned_package(tmp_path / "default-state.vpworkflow", "invoice_fixture", "1.0.0")
    install_workflow_package(inspect_workflow_package(package), root, reserved_workflow_ids=set())
    manager = WorkflowManager.with_available_workflows(workflow_root=root)
    store = WorkflowStateStore(
        tmp_path / "workflow_state.json",
        manager=manager,
        default_workflow_id="invoice_fixture",
    )
    original = store.load_or_migrate()
    assert original.active_workflow_id == "invoice_fixture"

    deactivated = store.commit_default_workflow(
        None, expected_current_workflow_id="invoice_fixture"
    )
    assert deactivated.active_workflow_id is None
    assert deactivated.revision == original.revision + 1
    assert store.load_existing().active_workflow_id is None


def test_workflow_update_ui_rejects_same_or_lower_version_before_confirmation():
    import ast
    qt = (Path(__file__).resolve().parents[1] / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    tree = ast.parse(qt)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_update_workflow_from_inspection")
    source = ast.get_source_segment(qt, method) or ""
    assert "compare_workflow_versions(manifest.version, current.version) <= 0" in source
    assert source.index("compare_workflow_versions") < source.index('"Trust and update workflow"')


def test_load_is_fail_closed_when_lifecycle_recovery_is_unresolved():
    import ast
    qt = (Path(__file__).resolve().parents[1] / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    tree = ast.parse(qt)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "load_workflow_plugin")
    source = ast.get_source_segment(qt, method) or ""
    assert "self.workflow_lifecycle_error" in source
    assert 'self.workflow_plugin_root / ".transactions"' in source
    assert source.index("workflow_lifecycle_error") < source.index("QFileDialog.getOpenFileName")


def test_unresolved_lifecycle_transaction_blocks_browser_automation_and_new_tasks():
    import ast
    qt = (Path(__file__).resolve().parents[1] / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    tree = ast.parse(qt)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    methods = {n.name: ast.get_source_segment(qt, n) or "" for n in cls.body if isinstance(n, ast.FunctionDef)}
    assert "self.workflow_lifecycle_error" in methods["can_open_task_browser"]
    assert "self.workflow_lifecycle_error" in methods["add_task"]
    assert "Workflow lifecycle recovery" in qt


def test_package_mutation_api_fails_closed_while_lifecycle_transaction_is_pending(tmp_path: Path):
    from vibrapilot.workflow import inspect_workflow_package, install_workflow_package

    root = tmp_path / "Workflows"
    pending = root / ".transactions" / "stale"
    pending.mkdir(parents=True)
    package = _versioned_package(tmp_path / "blocked.vpworkflow", "invoice_fixture", "1.0.0")
    with pytest.raises(Exception, match="pending workflow lifecycle transaction"):
        install_workflow_package(inspect_workflow_package(package), root, reserved_workflow_ids=set())


def test_remove_rejects_path_like_workflow_ids_before_filesystem_mutation(tmp_path: Path):
    from vibrapilot.workflow import remove_installed_workflow

    root = tmp_path / "Workflows"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    for unsafe in ("../outside", r"..\\outside", "C:outside", ".", ".."):
        with pytest.raises(Exception, match="safe installed workflow identifier"):
            remove_installed_workflow(unsafe, root)
    assert outside.is_dir()


def test_lifecycle_recovery_fails_closed_on_unexpected_transaction_root_file(tmp_path: Path):
    from vibrapilot.workflow import recover_workflow_lifecycle_transactions

    root = tmp_path / "Workflows"
    tx_root = root / ".transactions"
    tx_root.mkdir(parents=True)
    (tx_root / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(Exception, match="unexpected entries"):
        recover_workflow_lifecycle_transactions(root)
