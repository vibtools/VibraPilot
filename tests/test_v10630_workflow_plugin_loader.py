from __future__ import annotations

import json
from pathlib import Path
import sys
import zipfile

import pytest

from vibrapilot.workflow import (
    WorkflowPluginInstallError,
    WorkflowPluginValidationError,
    inspect_workflow_package,
    install_workflow_package,
)
from _v10630_plugin_fixture import write_plugin_package


def test_inspect_then_atomic_install_without_import_before_trust(tmp_path: Path):
    package = write_plugin_package(tmp_path / "invoice.vpworkflow")
    inspection = inspect_workflow_package(package)
    assert inspection.manifest.workflow_id == "invoice_fixture"
    assert inspection.plugin_api == 1
    assert inspection.task_schema.role_field("target_url") is not None
    install_root = tmp_path / "Workflows"
    installed = install_workflow_package(
        inspection, install_root, reserved_workflow_ids={"share_invite"}
    )
    assert installed.root == (install_root / "invoice_fixture").resolve()
    assert installed.runtime_factory is not None
    metadata = json.loads((installed.root / ".vibrapilot-plugin.json").read_text())
    assert metadata["package_sha256"] == inspection.package_sha256


def test_reserved_builtin_id_is_rejected(tmp_path: Path):
    package = write_plugin_package(tmp_path / "reserved.vpworkflow", "share_invite")
    inspection = inspect_workflow_package(package)
    with pytest.raises(WorkflowPluginInstallError, match="reserved"):
        install_workflow_package(inspection, tmp_path / "Workflows", reserved_workflow_ids={"share_invite"})


def test_archive_traversal_and_extra_python_are_rejected(tmp_path: Path):
    package = tmp_path / "bad.vpworkflow"
    write_plugin_package(package)
    with zipfile.ZipFile(package, "a") as archive:
        archive.writestr("../escape.txt", b"no")
    with pytest.raises(WorkflowPluginValidationError, match="Unsafe workflow package path"):
        inspect_workflow_package(package)

    package2 = tmp_path / "bad2.vpworkflow"
    write_plugin_package(package2)
    with zipfile.ZipFile(package2, "a") as archive:
        archive.writestr("helper.py", b"x=1")
    with pytest.raises(WorkflowPluginValidationError, match="Unsupported workflow package top-level entry: helper.py"):
        inspect_workflow_package(package2)


def test_trusted_module_sys_path_mutation_is_rejected_and_restored(tmp_path: Path):
    source = '''\
import sys
sys.path.append("MUTATED_BY_TEST")
class Runtime:
    def session_ready(self, page): return True
    def ensure_session(self): return None
    def execute_item(self, item): return "ok"
    def prepare_retry(self): return None
def create_workflow(host, **kwargs): return Runtime()
'''
    package = write_plugin_package(tmp_path / "mutator.vpworkflow", mutate={"workflow.py": source})
    before_inspect = list(sys.path)
    inspection = inspect_workflow_package(package)
    assert sys.path == before_inspect
    before = list(sys.path)
    with pytest.raises(WorkflowPluginValidationError, match="mutate sys.path"):
        install_workflow_package(inspection, tmp_path / "Workflows", reserved_workflow_ids={"share_invite"})
    assert sys.path == before
