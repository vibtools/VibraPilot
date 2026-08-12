from __future__ import annotations

import json
from pathlib import Path
import zipfile


def plugin_payload(workflow_id: str = "invoice_fixture") -> dict[str, object]:
    return {
        "manifest.json": {
            "workflow_id": workflow_id,
            "name": "Invoice Fixture",
            "description": "Test-only trusted workflow fixture.",
            "version": "1.0.0",
            "logo": "assets/logo.png",
            "entrypoint": "create_workflow",
            "plugin_api": 1,
        },
        "inputs.json": {
            "title": "Invoice Global Inputs",
            "fields": [
                {"key": "company_name", "label": "Company Name", "kind": "text", "default": ""},
                {"key": "tax_rate", "label": "Tax Rate", "kind": "decimal", "default": "0"},
            ],
        },
        "settings.json": {
            "title": "Invoice Settings",
            "fields": [
                {"key": "max_retry", "label": "Max Retry", "kind": "integer", "default": 2, "minimum": 0, "maximum": 9},
                {"key": "download_pdf", "label": "Download PDF", "kind": "boolean", "default": True},
            ],
        },
        "task.json": {
            "title": "Invoice Task Settings",
            "single_item": False,
            "requires_session": False,
            "uses_test_send_limit": False,
            "inputs": [
                {"key": "source_file", "label": "Source File", "kind": "file", "default": "", "required": True, "role": "data_file"},
            ],
            "settings": [
                {"key": "target_url", "label": "Target URL", "kind": "url", "default": "", "required": True, "role": "target_url"},
            ],
            "metrics": [
                {"key": "created", "label": "Created", "source": "workflow", "visible": True},
                {"key": "failed", "label": "Failed", "source": "core_failed", "visible": True},
            ],
        },
        "workflow.py": '''\
from pathlib import Path

class Runtime:
    def __init__(self, host, **kwargs):
        self.host = host
    def session_ready(self, page):
        return True
    def ensure_session(self):
        return None
    def execute_item(self, item):
        self.host.set_workflow_step("Creating invoice")
        self.host.set_workflow_metric("created", 1)
        return "fixture-ok"
    def prepare_retry(self):
        return None
    def classify_error(self, exc):
        return "FAIL_ITEM"

def create_workflow(host, **kwargs):
    return Runtime(host, **kwargs)

def load_task_items(path: Path, task_values):
    lines = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return [{"record": value} for value in lines]
''',
        "assets/logo.png": b"fixture-logo",
    }


def write_plugin_package(path: Path, workflow_id: str = "invoice_fixture", *, mutate: dict[str, object] | None = None) -> Path:
    payload = plugin_payload(workflow_id)
    if mutate:
        payload.update(mutate)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in payload.items():
            if isinstance(value, (dict, list)):
                data = json.dumps(value, indent=2).encode("utf-8")
            elif isinstance(value, str):
                data = value.encode("utf-8")
            else:
                data = bytes(value)
            archive.writestr(name, data)
    return path
