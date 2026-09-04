from __future__ import annotations

import importlib.util
import json
import threading
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibrapilot.workflow import inspect_workflow_package, install_workflow_package

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workflows" / "fiskl_invoice_sender"


def _load_module():
    spec = importlib.util.spec_from_file_location("test_fiskl_workflow", SOURCE / "workflow.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_package(path: Path) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(SOURCE.rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts and source.suffix != ".pyc":
                archive.write(source, source.relative_to(SOURCE).as_posix())
    return path


def test_source_package_inspects_installs_and_exposes_plugin_api(tmp_path: Path):
    package = _build_package(tmp_path / "Fiskl_Invoice_Sender_v1.0.0.vpworkflow")
    inspection = inspect_workflow_package(package)
    assert inspection.manifest.workflow_id == "fiskl_invoice_sender"
    assert inspection.manifest.version == "1.0.0"
    assert inspection.plugin_api == 1
    assert inspection.task_schema.requires_session is True
    assert inspection.task_schema.uses_test_send_limit is False
    assert inspection.task_schema.role_field("data_file") is not None
    assert inspection.task_schema.role_field("target_url") is None
    installed = install_workflow_package(
        inspection, tmp_path / "Workflows", reserved_workflow_ids=set()
    )
    assert installed.task_data_loader is not None
    assert callable(installed.runtime_factory)


def test_txt_loader_validates_deduplicates_and_batches(tmp_path: Path):
    module = _load_module()
    source = tmp_path / "emails.txt"
    source.write_text(
        "one@example.com\ninvalid\nTWO@example.com\none@example.com\nthree@example.com\n",
        encoding="utf-8",
    )
    loaded = module.load_task_data(
        source,
        {"per_sending_total_email": 2},
        {"remove_duplicates": True},
    )
    assert len(loaded["items"]) == 2
    assert json.loads(loaded["items"][0]["emails_json"]) == ["one@example.com", "TWO@example.com"]
    assert json.loads(loaded["items"][1]["emails_json"]) == ["three@example.com"]
    assert loaded["items"][0]["recipient_count"] == 2
    assert "invalid 1" in loaded["summary"]
    assert "duplicates removed 1" in loaded["summary"]
    assert len(loaded["source_fingerprint"]) == 64


def test_csv_loader_uses_named_email_column(tmp_path: Path):
    module = _load_module()
    source = tmp_path / "emails.csv"
    source.write_text("name,email\nOne,one@example.com\nTwo,two@example.com\n", encoding="utf-8")
    loaded = module.load_task_data(source, {"per_sending_total_email": 8}, {})
    assert json.loads(loaded["items"][0]["emails_json"]) == ["one@example.com", "two@example.com"]


@pytest.mark.parametrize("value", [0, -1, "bad"])
def test_loader_rejects_invalid_batch_size(tmp_path: Path, value):
    module = _load_module()
    source = tmp_path / "emails.txt"
    source.write_text("one@example.com\n", encoding="utf-8")
    with pytest.raises(module.InvalidWorkflowData, match="Per Sending Total Email"):
        module.load_task_data(source, {"per_sending_total_email": value}, {})


def test_dynamic_fiskl_invoice_url_contract():
    module = _load_module()
    assert module.FisklInvoiceWorkflow._url_is_invoice(
        "https://app.fiskl.com/dashboard/invoices/350821"
    )
    assert module.FisklInvoiceWorkflow._url_is_invoice(
        "https://app.fiskl.com/dashboard/invoices/another-id?view=send"
    )
    assert not module.FisklInvoiceWorkflow._url_is_invoice(
        "https://app.fiskl.com/dashboard/invoices"
    )
    assert not module.FisklInvoiceWorkflow._url_is_invoice(
        "http://app.fiskl.com/dashboard/invoices/350821"
    )
    assert not module.FisklInvoiceWorkflow._url_is_invoice(
        "https://evil.example/dashboard/invoices/350821"
    )


def test_periodic_test_send_count_crosses_exact_intervals():
    module = _load_module()

    class Host:
        def __init__(self):
            self.state = SimpleNamespace(
                current_index=0,
                items=[
                    SimpleNamespace(
                        email="",
                        result=module.FisklInvoiceWorkflow._encode_result(
                            normal_confirmed=True,
                            tests_confirmed=0,
                        ),
                        status="success",
                    ),
                    SimpleNamespace(email="", result="", status="pending"),
                ],
            )
            self.workflow_item_payloads = tuple(
                {
                    "recipient_count": 8,
                    "emails_json": json.dumps(
                        [f"{prefix}{number}@example.com" for number in range(1, 9)]
                    ),
                }
                for prefix in ("a", "b")
            )
            self.workflow_settings_values = {
                "test_emails": "qa@example.com",
                "after_send_test_email": 10,
            }
            self.workflow_task_values = {}
            self.workflow_input_values = {}
            self.settings = {}

        def set_workflow_metric(self, *_args):
            pass

    runtime = module.FisklInvoiceWorkflow(Host())
    assert runtime._tests_due_for_index(0) == 0
    assert runtime._tests_due_for_index(1) == 1


def test_source_does_not_embed_reference_pii_or_signed_url():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SOURCE.rglob("*")
        if path.is_file() and path.suffix.lower() in {".py", ".json", ".md", ".txt"}
    )
    assert "shahinalomm373765@gmail.com" not in combined
    assert "X-Amz-Signature" not in combined
    assert "/dashboard/invoices/350821" not in combined


def _runtime_host(module, *, result: str = "", interval: int = 4):
    item = SimpleNamespace(
        email="one@example.com, two@example.com, three@example.com, four@example.com",
        result=result,
        status="pending",
        message="",
        attempts=0,
    )

    class Host:
        def __init__(self):
            self.state = SimpleNamespace(
                current_index=0,
                items=[item],
                manual_review_required=False,
                success_count=0,
                failed_count=0,
            )
            self.workflow_item_payloads = (
                {
                    "recipient_count": 4,
                    "emails_json": json.dumps(
                        [
                            "one@example.com",
                            "two@example.com",
                            "three@example.com",
                            "four@example.com",
                        ]
                    ),
                },
            )
            self.workflow_settings_values = {
                "test_emails": "qa@example.com",
                "after_send_test_email": interval,
            }
            self.workflow_task_values = {"sending_delay": 0}
            self.workflow_input_values = {
                "email_subject": "Invoice",
                "email_message": "Message",
            }
            self.settings = {}
            self.stop_event = threading.Event()
            self.close_event = threading.Event()

        def set_workflow_metric(self, key, value):
            self.metrics = getattr(self, "metrics", {})
            self.metrics[key] = value

        def set_workflow_step(self, value):
            self.step = value

        def log(self, *_args):
            pass

    return Host(), item


def test_process_item_persists_normal_and_periodic_test_phases():
    module = _load_module()
    host, item = _runtime_host(module, interval=2)
    runtime = module.FisklInvoiceWorkflow(host)
    calls = []
    runtime._send_with_retry = lambda index, task_item, emails, phase: calls.append(
        (index, emails, phase)
    )
    runtime.process_item(0, item)
    assert [phase for _index, _emails, phase in calls] == ["normal", "test 1/2", "test 2/2"]
    assert runtime._decode_result(item.result) == {"normal_confirmed": True, "tests_confirmed": 2}
    assert item.status == "success"
    assert host.state.success_count == 1
    assert host.metrics["sent_recipients"] == 4
    assert host.metrics["test_sends"] == 2


def test_process_item_recovery_does_not_replay_confirmed_normal_send():
    module = _load_module()
    prior = module.FisklInvoiceWorkflow._encode_result(normal_confirmed=True, tests_confirmed=1)
    host, item = _runtime_host(module, result=prior, interval=2)
    runtime = module.FisklInvoiceWorkflow(host)
    calls = []
    runtime._send_with_retry = lambda index, task_item, emails, phase: calls.append(phase)
    runtime.process_item(0, item)
    assert calls == ["test 2/2"]
    assert runtime._decode_result(item.result) == {"normal_confirmed": True, "tests_confirmed": 2}
    assert host.metrics["sent_recipients"] == 4


def test_uncertain_send_requires_manual_review_without_failure_advance():
    module = _load_module()
    host, item = _runtime_host(module)
    runtime = module.FisklInvoiceWorkflow(host)

    def uncertain(*_args):
        raise module.SendOutcomeUncertain("confirmation missing")

    runtime._send_with_retry = uncertain
    runtime.process_item(0, item)
    assert item.status == "interrupted"
    assert host.state.manual_review_required is True
    assert host.state.success_count == 0
    assert host.state.failed_count == 0
    assert "Manual review required" in item.message
