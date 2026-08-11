from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibrapilot.workflow import (
    RECOVERY_COMMITTED,
    RECOVERY_PREPARED,
    WORKFLOW_RECOVERY_TRANSACTION_SCHEMA_VERSION,
    WorkflowManager,
    WorkflowManifest,
    WorkflowRecoveryError,
    WorkflowRecoveryTransaction,
    WorkflowRegistry,
    WorkflowStateCorruptError,
    WorkflowStateError,
    WorkflowStateStore,
)
from vibrapilot.workflow.share_invite import SHARE_INVITE_MANIFEST


class DummyRuntime:
    def __init__(self, manifest: WorkflowManifest) -> None:
        self.manifest = manifest

    def session_ready(self, page) -> bool:
        return True

    def ensure_session(self) -> None:
        return None

    def execute_item(self, item) -> str:
        return "ok"

    def prepare_retry(self) -> None:
        return None


def _other_manifest() -> WorkflowManifest:
    return WorkflowManifest(
        workflow_id="other_workflow",
        name="Other Workflow",
        description="Synthetic PR-10 recovery target.",
        version="1.0",
        logo="assets/other.png",
        entrypoint="other_workflow",
    )


def _manager() -> WorkflowManager:
    other = _other_manifest()
    return WorkflowManager(
        WorkflowRegistry([SHARE_INVITE_MANIFEST, other]),
        runtime_factories={
            "share_invite": lambda *args, **kwargs: DummyRuntime(SHARE_INVITE_MANIFEST),
            "other_workflow": lambda *args, **kwargs: DummyRuntime(other),
        },
    )


def test_recovery_transaction_contract_is_schema_v1_prepared_committed():
    assert WORKFLOW_RECOVERY_TRANSACTION_SCHEMA_VERSION == 1
    assert RECOVERY_PREPARED == "PREPARED"
    assert RECOVERY_COMMITTED == "COMMITTED"


def test_explicit_state_recovery_quarantines_invalid_canonical_and_uses_revision_one(tmp_path: Path):
    path = tmp_path / "workflow_state.json"
    path.write_text("{broken", encoding="utf-8")
    store = WorkflowStateStore(path, manager=_manager())

    recovered = store.recover_active_workflow("other_workflow")

    assert recovered.active_workflow_id == "other_workflow"
    assert recovered.schema_version == 1
    assert recovered.revision == 1
    assert store.load_existing() == recovered
    quarantined = list(tmp_path.glob("workflow_state.json.corrupt-*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding="utf-8") == "{broken"


def test_explicit_state_recovery_refuses_to_overwrite_valid_canonical(tmp_path: Path):
    store = WorkflowStateStore(tmp_path / "workflow_state.json", manager=_manager())
    original = store.load_or_migrate()
    with pytest.raises(WorkflowStateError, match="valid canonical state already exists"):
        store.recover_active_workflow("other_workflow")
    assert store.load_existing() == original


def test_prepared_recovery_without_committed_state_rolls_back_exact_staged_data(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    store = WorkflowStateStore(data / "workflow_state.json", manager=_manager())
    # Simulate already-quarantined unavailable workflow state.
    (data / "workflow_state.json.corrupt-evidence").write_text("broken", encoding="utf-8")
    settings = data / "settings.json"
    settings.write_bytes(b"before")
    absent = data / "slot_9_checkpoint.json"

    tx = WorkflowRecoveryTransaction(
        data_root=data,
        transaction_root=data / "WorkflowRecovery",
        target_workflow_id="other_workflow",
    )
    tx.prepare([settings, absent])
    settings.write_bytes(b"after")
    absent.write_bytes(b"created")

    actions = WorkflowRecoveryTransaction.recover_all(
        data_root=data,
        transaction_root=data / "WorkflowRecovery",
        state_store=store,
    )

    assert settings.read_bytes() == b"before"
    assert not absent.exists()
    assert actions and actions[0].startswith("rolled back prepared recovery")
    assert (data / "workflow_state.json.corrupt-evidence").is_file()


def test_recovery_state_commit_is_authoritative_even_before_committed_marker(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    store = WorkflowStateStore(data / "workflow_state.json", manager=_manager())
    (data / "workflow_state.json.corrupt-evidence").write_text("broken", encoding="utf-8")
    runtime = data / "task_runtime.sqlite3"
    runtime.write_bytes(b"old-runtime")

    tx = WorkflowRecoveryTransaction(
        data_root=data,
        transaction_root=data / "WorkflowRecovery",
        target_workflow_id="other_workflow",
    )
    tx.prepare([runtime])
    runtime.unlink()
    store.recover_active_workflow("other_workflow")
    # Crash before mark_committed(). Startup must treat target state as committed.
    actions = WorkflowRecoveryTransaction.recover_all(
        data_root=data,
        transaction_root=data / "WorkflowRecovery",
        state_store=store,
    )

    assert store.load_existing().active_workflow_id == "other_workflow"
    assert not runtime.exists(), "old runtime must never be resurrected post-commit"
    assert actions and actions[0].startswith("cleaned committed recovery")


def test_marked_committed_recovery_without_canonical_state_hard_fails(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    store = WorkflowStateStore(data / "workflow_state.json", manager=_manager())
    tx = WorkflowRecoveryTransaction(
        data_root=data,
        transaction_root=data / "WorkflowRecovery",
        target_workflow_id="other_workflow",
    )
    tx.prepare([])
    tx.mark_committed()

    with pytest.raises(WorkflowRecoveryError, match="no canonical workflow state"):
        WorkflowRecoveryTransaction.recover_all(
            data_root=data,
            transaction_root=data / "WorkflowRecovery",
            state_store=store,
        )
    assert tx.path.is_dir(), "ambiguous recovery evidence must not be deleted"


def test_malformed_recovery_manifest_hard_fails_without_deleting_evidence(tmp_path: Path):
    data = tmp_path / "AppData"
    root = data / "WorkflowRecovery" / "bad"
    root.mkdir(parents=True)
    manifest = root / "transaction.json"
    manifest.write_text("{broken", encoding="utf-8")
    store = WorkflowStateStore(data / "workflow_state.json", manager=_manager())

    with pytest.raises(WorkflowRecoveryError, match="manifest is invalid"):
        WorkflowRecoveryTransaction.recover_all(
            data_root=data,
            transaction_root=data / "WorkflowRecovery",
            state_store=store,
        )
    assert manifest.read_text(encoding="utf-8") == "{broken"


def test_ambiguous_target_state_hard_fails_and_preserves_staging(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    store = WorkflowStateStore(data / "workflow_state.json", manager=_manager())
    store.load_or_migrate()  # share_invite is valid, but tx target is other_workflow.
    tx = WorkflowRecoveryTransaction(
        data_root=data,
        transaction_root=data / "WorkflowRecovery",
        target_workflow_id="other_workflow",
    )
    tx.prepare([])

    with pytest.raises(WorkflowRecoveryError, match="ambiguous workflow recovery transaction"):
        WorkflowRecoveryTransaction.recover_all(
            data_root=data,
            transaction_root=data / "WorkflowRecovery",
            state_store=store,
        )
    assert tx.path.is_dir()


def test_recovery_transaction_rejects_paths_outside_appdata(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    tx = WorkflowRecoveryTransaction(
        data_root=data,
        transaction_root=data / "WorkflowRecovery",
        target_workflow_id="share_invite",
    )
    with pytest.raises(WorkflowRecoveryError, match="escapes AppData boundary"):
        tx.prepare([outside])
    assert not tx.path.exists()
