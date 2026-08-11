#!/usr/bin/env python3
"""PR-11 target-Windows acceptance runner for VibraPilot v1.0.6.28.

Verification tooling only. It does not edit production settings/source files, delete
runtime data, touch personal Chrome User Data, or terminate arbitrary Chrome processes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

EXPECTED_PYTHON = (3, 12)
EXPECTED_PLAYWRIGHT = "1.61.0"
EVIDENCE_SCHEMA_VERSION = 1
ALLOWED_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "OWNER_ACCEPTED_RESIDUAL"}

GATES = [
    ("G01", "Environment and Chrome identity", True),
    ("G02", "Browser Open -> Close -> Reopen lifecycle", True),
    ("G03", "Repeated lifecycle cycles without stale state", True),
    ("G04", "Manual Chrome window close detection and reopen", True),
    ("G05", "Exact managed-process termination and recovery", True),
    ("G06", "Real Task-specific download", True),
    ("G07", "Download filename/content/hash verification", True),
    ("G08", "Same-filename collision-safe download", True),
    ("G09", "Download after close/reopen", True),
    ("G10", "Single-file website chooser", True),
    ("G11", "Multiple-file chooser where supported", True),
    ("G12", "Directory upload where control supports it", True),
    ("G13", "File chooser cancel behavior", True),
    ("G14", "Stale chooser rejection after close/reopen", True),
    ("G15", "Cross-Task chooser isolation", True),
    ("G16", "Managed profile persistence markers", True),
    ("G17", "Cross-Task web-storage/profile isolation", True),
    ("G18", "Chrome Web Store extension persistence", True),
    ("G19", "Unpacked-extension runtime/manifest regression", True),
    ("G20", "One-Task control matrix", True),
    ("G21", "Two simultaneous Task isolation", True),
    ("G22", "Four simultaneous Task isolation", True),
    ("G23", "One Task close/crash does not affect another", True),
    ("G24", "Independent managed profile paths", True),
    ("G25", "Independent managed download paths", True),
    ("G26", "Independent chooser state", True),
    ("G27", "Independent browser/UI lifecycle state", True),
    ("G28", "Manual-review Task isolation regression", True),
    ("G29", "PR-10 healthy recovery/runtime preflight regression", True),
    ("G30", "Sandbox-OFF control matrix", True),
    ("G31", "Sandbox-ON compatibility matrix", True),
    ("G32", "Healthy Google Chrome path; fallback_used=false", True),
    ("G33", "Controlled Chromium fallback verification", False),
    ("G34", "Final Chrome/fallback policy evidence", True),
    ("G35", "Full Windows/Python 3.12 source regression", True),
]

INSTRUCTIONS = {
    "G02": "Use one Task: Open Browser -> Close Browser -> Open Browser. Confirm Opening/Open/Closing/Closed states and same slot profile.",
    "G03": "Repeat normal Open/Close/Reopen five cycles. Stop on the first reproducible failure.",
    "G04": "Open the managed Chrome window, close it using the window X, wait for VibraPilot to reflect closure, then reopen.",
    "G05": "Capture slot diagnostics first. Terminate ONLY the exact managed root PID whose sanitized diagnostic profile matches the Task, then verify recovery/reopen.",
    "G06": "Open the local PR-11 test page in the Task browser and click Download PR11 File.",
    "G07": "Verify downloaded file name, size and SHA-256 using the runner's fixture manifest.",
    "G08": "Download the same PR11 file again and verify the previous file was not overwritten.",
    "G10": "Use the local page single-file chooser with pr11-single.txt.",
    "G11": "Use the multiple chooser with pr11-multi-a.txt and pr11-multi-b.txt.",
    "G12": "Use the directory chooser with PR11Directory only where the website control exposes directory upload.",
    "G16": "On the local page set the slot marker, close/reopen the same Task browser, then confirm cookie/localStorage/IndexedDB marker persistence.",
    "G17": "Set distinct local markers in slot_1 and slot_2 and prove neither Task sees the other's marker/profile.",
    "G18": "Use the already approved Chrome Web Store path. Record extension ID only; verify persistence after close/reopen.",
    "G19": "Use a harmless valid unpacked extension and verify manifest/runtime/close-reopen plus upload/download regression. Also test invalid path/manifest rejection.",
    "G21": "Run slot_1 and slot_2 simultaneously; verify profiles, storage, chooser, download and lifecycle isolation.",
    "G22": "Run slot_1..slot_4 simultaneously; verify unique profiles and independent lifecycle/capability state.",
    "G28": "Use isolated automated/Test Mode evidence only; do not send real bulk invitations.",
    "G30": "Run the control matrix with the production default Sandbox OFF.",
    "G31": "Temporarily test Sandbox ON through the existing setting only. Restore the prior value after testing; this does not authorize a default-source change.",
    "G33": "Test fallback only if it can be done safely. Otherwise use OWNER_ACCEPTED_RESIDUAL with explicit owner acceptance; never fabricate PASS.",
    "G34": "Record the final policy decision: Chrome preferred with observable fallback retained unless separately approved otherwise.",
    "G35": "Run the supplied PR-11 DEV verifier/source regression command and record its final result.",
}

TEST_DOWNLOAD = b"VibraPilot PR-11 deterministic download fixture\n"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_root(root: Path) -> Path:
    override = os.environ.get("VIB_TOOLS_DATA_DIR", "").strip()
    return Path(override).expanduser().resolve() if override else root


def default_evidence_root(root: Path) -> Path:
    return data_root(root) / "AppData" / "PR11Acceptance"


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{uuid.uuid4().hex}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def detect_chrome() -> dict[str, Any]:
    if os.name != "nt":
        return {"found": False, "reason": "not_windows"}
    candidates: list[Path] = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")
    explicit = os.environ.get("VIBRAPILOT_CHROME_EXE", "").strip()
    if explicit:
        candidates.insert(0, Path(explicit))
    for path in candidates:
        if path.is_file():
            return {
                "found": True,
                "executable": str(path.resolve()),
                "version": "captured_later_by_browser_diagnostics",
            }
    return {"found": False, "reason": "chrome_stable_not_found_in_standard_paths"}


def environment_snapshot(root: Path) -> dict[str, Any]:
    try:
        playwright_version = importlib.metadata.version("playwright")
    except Exception:
        playwright_version = "unknown"
    defaults = {}
    defaults_path = root / "config" / "settings.defaults.json"
    if defaults_path.is_file():
        try:
            defaults = load_json(defaults_path)
        except Exception:
            defaults = {}
    chrome = detect_chrome()
    return {
        "captured_at": now_iso(),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "playwright": playwright_version,
        "expected_playwright": EXPECTED_PLAYWRIGHT,
        "chrome": chrome,
        "data_root": str(data_root(root)),
        "browser_defaults": {
            "sandbox_enabled": defaults.get("sandbox_enabled"),
            "allow_chromium_fallback": defaults.get("allow_chromium_fallback"),
            "use_persistent_context": defaults.get("use_persistent_context"),
            "accept_downloads": defaults.get("accept_downloads"),
            "auto_restart_browser_on_crash": defaults.get("auto_restart_browser_on_crash"),
            "browser_restart_max_attempts": defaults.get("browser_restart_max_attempts"),
        },
    }


def environment_pass(snapshot: dict[str, Any]) -> tuple[bool, list[str]]:
    failures = []
    if snapshot.get("system") != "Windows":
        failures.append("Target OS is not Windows.")
    machine = str(snapshot.get("machine") or "").lower()
    if machine not in {"amd64", "x86_64"}:
        failures.append(f"Target architecture is not x64: {snapshot.get('machine')}")
    version = tuple(sys.version_info[:2])
    if version != EXPECTED_PYTHON:
        failures.append(f"Python must be 3.12.x, current={platform.python_version()}")
    if snapshot.get("playwright") != EXPECTED_PLAYWRIGHT:
        failures.append(
            f"Playwright mismatch: current={snapshot.get('playwright')}, expected={EXPECTED_PLAYWRIGHT}"
        )
    chrome = snapshot.get("chrome") if isinstance(snapshot.get("chrome"), dict) else {}
    if not chrome.get("found"):
        failures.append("Google Chrome Stable was not found in standard paths.")
    defaults = snapshot.get("browser_defaults") if isinstance(snapshot.get("browser_defaults"), dict) else {}
    if defaults.get("sandbox_enabled") is not False:
        failures.append("Production default sandbox_enabled must remain false for PR-11 control.")
    if defaults.get("allow_chromium_fallback") is not True:
        failures.append("Production default allow_chromium_fallback must remain true during PR-11.")
    return not failures, failures


def init_run(root: Path, evidence_root: Path | None = None) -> Path:
    evidence_root = evidence_root or default_evidence_root(root)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = evidence_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    fixtures = run_dir / "fixtures"
    fixtures.mkdir()
    (fixtures / "pr11-single.txt").write_text("PR11 single upload fixture\n", encoding="utf-8")
    (fixtures / "pr11-multi-a.txt").write_text("PR11 multi A\n", encoding="utf-8")
    (fixtures / "pr11-multi-b.txt").write_text("PR11 multi B\n", encoding="utf-8")
    directory = fixtures / "PR11Directory"
    directory.mkdir()
    (directory / "alpha.txt").write_text("PR11 directory alpha\n", encoding="utf-8")
    (directory / "beta.txt").write_text("PR11 directory beta\n", encoding="utf-8")
    download_sha = hashlib.sha256(TEST_DOWNLOAD).hexdigest()
    write_json_atomic(fixtures / "manifest.json", {
        "download_filename": "pr11-download.txt",
        "download_size": len(TEST_DOWNLOAD),
        "download_sha256": download_sha,
        "upload_files": ["pr11-single.txt", "pr11-multi-a.txt", "pr11-multi-b.txt", "PR11Directory"],
    })
    env = environment_snapshot(root)
    write_json_atomic(run_dir / "environment.json", env)
    gates = {
        gate_id: {
            "title": title,
            "mandatory": mandatory,
            "status": "NOT_RUN",
            "note": "",
            "updated_at": None,
            "owner_accepted": False,
            "evidence": [],
        }
        for gate_id, title, mandatory in GATES
    }
    ok, failures = environment_pass(env)
    gates["G01"]["status"] = "NOT_RUN" if ok else "BLOCKED"
    gates["G01"]["note"] = (
        "Environment preflight passed; capture live BrowserDiagnostics to prove Google Chrome runtime identity."
        if ok else " | ".join(failures)
    )
    gates["G01"]["updated_at"] = now_iso()
    write_json_atomic(run_dir / "gates.json", {"schema_version": EVIDENCE_SCHEMA_VERSION, "gates": gates})
    write_json_atomic(run_dir / "run.json", {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": now_iso(),
        "target_version": "1.0.6.28",
        "baseline_version": "1.0.6.27",
        "production_source_changes": 0,
        "repo_root": str(root),
    })
    return run_dir


def sanitize_browser_record(record: dict[str, Any]) -> dict[str, Any]:
    actual = record.get("actual") if isinstance(record.get("actual"), dict) else {}
    launch = record.get("launch") if isinstance(record.get("launch"), dict) else {}
    requested = record.get("requested") if isinstance(record.get("requested"), dict) else {}
    playwright = record.get("playwright") if isinstance(record.get("playwright"), dict) else {}
    return {
        "captured_at": now_iso(),
        "slot_id": record.get("slot_id"),
        "actual": {
            "engine": actual.get("engine"),
            "product": actual.get("product"),
            "executable_path": actual.get("executable_path"),
            "pid": actual.get("pid"),
            "profile_path": actual.get("profile_path"),
            "process_status": actual.get("process_status"),
        },
        "requested": {
            "profile_path": requested.get("profile_path"),
            "profile_directory": requested.get("profile_directory"),
            "sandbox_enabled": requested.get("sandbox_enabled"),
            "persistent_context": requested.get("persistent_context"),
        },
        "launch": {
            "fallback_used": launch.get("fallback_used"),
            "fallback_reason_present": bool(launch.get("fallback_reason")),
        },
        "playwright": {
            "actual_version": playwright.get("actual_version") or record.get("playwright_python_version"),
            "expected_version": playwright.get("expected_version") or EXPECTED_PLAYWRIGHT,
        },
    }


def capture_browser(run_dir: Path, diagnostic: Path) -> Path:
    record = load_json(diagnostic)
    sanitized = sanitize_browser_record(record)
    slot = sanitized.get("slot_id") or "unknown"
    path = run_dir / "browser" / f"slot_{slot}_{int(time.time())}.json"
    write_json_atomic(path, sanitized)
    actual = sanitized.get("actual") if isinstance(sanitized.get("actual"), dict) else {}
    launch = sanitized.get("launch") if isinstance(sanitized.get("launch"), dict) else {}
    playwright = sanitized.get("playwright") if isinstance(sanitized.get("playwright"), dict) else {}
    identity_ok = bool(
        actual.get("engine") == "google_chrome"
        and actual.get("product")
        and actual.get("executable_path")
        and actual.get("profile_path")
        and launch.get("fallback_used") is False
        and playwright.get("actual_version") == EXPECTED_PLAYWRIGHT
    )
    note = (
        "Live BrowserDiagnostics confirms Google Chrome, managed profile, fallback_used=false and Playwright 1.61.0."
        if identity_ok else
        "Live BrowserDiagnostics did not satisfy the full healthy Google Chrome identity contract."
    )
    record_gate(
        run_dir, "G01", "PASS" if identity_ok else "BLOCKED", note,
        evidence=[path.relative_to(run_dir).as_posix()],
    )
    return path


def record_gate(run_dir: Path, gate_id: str, status: str, note: str, owner_accepted: bool = False,
                evidence: list[str] | None = None) -> None:
    status = status.upper()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status {status}; allowed={sorted(ALLOWED_STATUSES)}")
    if status == "OWNER_ACCEPTED_RESIDUAL" and not owner_accepted:
        raise ValueError("OWNER_ACCEPTED_RESIDUAL requires explicit --owner-accepted confirmation.")
    payload = load_json(run_dir / "gates.json")
    gates = payload.get("gates")
    if not isinstance(gates, dict) or gate_id not in gates:
        raise ValueError(f"Unknown gate: {gate_id}")
    gates[gate_id]["status"] = status
    gates[gate_id]["note"] = str(note or "")
    gates[gate_id]["owner_accepted"] = bool(owner_accepted)
    gates[gate_id]["updated_at"] = now_iso()
    gates[gate_id]["evidence"] = list(evidence or [])
    write_json_atomic(run_dir / "gates.json", payload)


def summarize(run_dir: Path) -> tuple[str, list[str]]:
    payload = load_json(run_dir / "gates.json")
    gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
    problems: list[str] = []
    for gate_id, title, mandatory in GATES:
        item = gates.get(gate_id, {}) if isinstance(gates.get(gate_id), dict) else {}
        status = item.get("status", "NOT_RUN")
        if status == "FAIL":
            problems.append(f"{gate_id} FAIL: {title}")
        elif mandatory and status in {"NOT_RUN", "BLOCKED"}:
            problems.append(f"{gate_id} {status}: {title}")
        elif status == "OWNER_ACCEPTED_RESIDUAL" and not item.get("owner_accepted"):
            problems.append(f"{gate_id} residual lacks explicit owner acceptance: {title}")
    if any("FAIL" in p for p in problems):
        return "FAIL", problems
    if problems:
        return "BLOCKED", problems
    return "PASS", []


class TestPageHandler(BaseHTTPRequestHandler):
    server_version = "VibraPilotPR11/1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/download/pr11-download.txt"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="pr11-download.txt"')
            self.send_header("Content-Length", str(len(TEST_DOWNLOAD)))
            self.end_headers()
            self.wfile.write(TEST_DOWNLOAD)
            return
        body = b"""<!doctype html><html><head><meta charset='utf-8'><title>VibraPilot PR-11 Acceptance</title></head>
<body><h1>VibraPilot PR-11 Acceptance Page</h1>
<p>This localhost page contains only harmless deterministic controls.</p>
<p><a id='download' href='/download/pr11-download.txt'>Download PR11 File</a></p>
<label>Single file <input id='single' type='file'></label><br>
<label>Multiple files <input id='multi' type='file' multiple></label><br>
<label>Directory <input id='directory' type='file' webkitdirectory directory multiple></label><br>
<button id='set-marker'>Set storage marker</button>
<button id='read-marker'>Read storage marker</button>
<pre id='output'></pre>
<script>
const out = document.getElementById('output');
async function idbSet(v){return new Promise((resolve,reject)=>{const r=indexedDB.open('vibrapilot_pr11',1);r.onupgradeneeded=()=>r.result.createObjectStore('markers');r.onerror=()=>reject(r.error);r.onsuccess=()=>{const db=r.result;const tx=db.transaction('markers','readwrite');tx.objectStore('markers').put(v,'slot');tx.oncomplete=()=>{db.close();resolve()};tx.onerror=()=>reject(tx.error)}})}
async function idbGet(){return new Promise((resolve,reject)=>{const r=indexedDB.open('vibrapilot_pr11',1);r.onupgradeneeded=()=>r.result.createObjectStore('markers');r.onerror=()=>reject(r.error);r.onsuccess=()=>{const db=r.result;const tx=db.transaction('markers');const q=tx.objectStore('markers').get('slot');q.onsuccess=()=>{db.close();resolve(q.result||null)};q.onerror=()=>reject(q.error)}})}
document.getElementById('set-marker').onclick=async()=>{const v=prompt('Enter a harmless slot marker, e.g. SLOT_1_A'); if(!v)return; localStorage.setItem('pr11-slot',v); document.cookie='pr11_slot='+encodeURIComponent(v)+'; path=/; SameSite=Lax'; await idbSet(v); history.pushState({},'', '/history-marker-'+encodeURIComponent(v)); out.textContent='marker set: '+v};
document.getElementById('read-marker').onclick=async()=>{const idb=await idbGet(); out.textContent=JSON.stringify({localStorage:localStorage.getItem('pr11-slot'),cookiePresent:document.cookie.includes('pr11_slot='),indexedDB:idb,historyPath:location.pathname},null,2)};
</script></body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(run_dir: Path, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), TestPageHandler)
    actual_port = server.server_address[1]
    write_json_atomic(run_dir / "test_server.json", {
        "started_at": now_iso(), "host": host, "port": actual_port,
        "url": f"http://{host}:{actual_port}/",
        "download_sha256": hashlib.sha256(TEST_DOWNLOAD).hexdigest(),
    })
    print(f"PR-11 local test page: http://{host}:{actual_port}/")
    print("Leave this CMD window open during download/upload/storage gates. Ctrl+C stops only this local server.")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def safe_kill_from_diagnostic(diagnostic: Path, expected_pid: int, confirm: bool) -> int:
    if os.name != "nt":
        print("BLOCKED: managed-process termination is Windows-only.")
        return 2
    record = load_json(diagnostic)
    sanitized = sanitize_browser_record(record)
    actual = sanitized.get("actual") if isinstance(sanitized.get("actual"), dict) else {}
    pid = actual.get("pid")
    profile = str(actual.get("profile_path") or sanitized.get("requested", {}).get("profile_path") or "")
    executable = str(actual.get("executable_path") or "")
    if not isinstance(pid, int) or pid <= 0 or pid != expected_pid:
        print(f"BLOCKED: diagnostic PID mismatch; captured={pid}, requested={expected_pid}")
        return 2
    if "BrowserProfiles" not in profile and "VibraPilot" not in profile:
        print(f"BLOCKED: profile path is not recognizable as managed VibraPilot evidence: {profile}")
        return 2
    if executable and Path(executable).name.lower() not in {"chrome.exe", "chromium.exe"}:
        print(f"BLOCKED: captured executable is not Chrome/Chromium: {executable}")
        return 2
    if not confirm:
        print(f"SAFE KILL READY: PID={pid} profile={profile}")
        print("Re-run with --confirm-pid to terminate ONLY this diagnostic-identified managed PID tree.")
        return 3
    completed = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
    return completed.returncode


def interactive(run_dir: Path) -> int:
    payload = load_json(run_dir / "gates.json")
    gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
    print(f"PR-11 run: {run_dir}")
    print("Statuses: p=PASS, f=FAIL, b=BLOCKED, r=OWNER_ACCEPTED_RESIDUAL, s=skip/NOT_RUN, q=quit")
    for gate_id, title, mandatory in GATES:
        current = gates.get(gate_id, {}).get("status", "NOT_RUN") if isinstance(gates.get(gate_id), dict) else "NOT_RUN"
        if current in {"PASS", "OWNER_ACCEPTED_RESIDUAL"}:
            continue
        print(f"\n[{gate_id}] {title} | current={current} | mandatory={mandatory}")
        if gate_id in INSTRUCTIONS:
            print(INSTRUCTIONS[gate_id])
        answer = input("Result [p/f/b/r/s/q]: ").strip().lower()
        if answer == "q":
            break
        mapping = {"p": "PASS", "f": "FAIL", "b": "BLOCKED", "r": "OWNER_ACCEPTED_RESIDUAL", "s": "NOT_RUN"}
        if answer not in mapping:
            print("Invalid input; leaving gate unchanged.")
            continue
        note = input("Short sanitized note/evidence summary: ").strip()
        owner = answer == "r"
        record_gate(run_dir, gate_id, mapping[answer], note, owner_accepted=owner)
        if answer == "f":
            print("STOP: reproducible failure recorded. Do not retry it away; report this gate for product-vs-harness classification.")
            break
    status, problems = summarize(run_dir)
    print(f"\nPR-11 EVIDENCE SUMMARY: {status}")
    for item in problems:
        print(" -", item)
    return 0 if status == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="VibraPilot PR-11 Windows acceptance runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create a new sanitized PR-11 acceptance run")
    p_init.add_argument("--evidence-root", type=Path)

    p_env = sub.add_parser("environment", help="Capture/print target environment")
    p_env.add_argument("--run-dir", type=Path)

    p_serve = sub.add_parser("serve", help="Serve the harmless localhost PR-11 test page")
    p_serve.add_argument("--run-dir", type=Path, required=True)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=0)

    p_capture = sub.add_parser("capture-browser", help="Copy a sanitized browser diagnostic into acceptance evidence")
    p_capture.add_argument("--run-dir", type=Path, required=True)
    p_capture.add_argument("--diagnostic", type=Path, required=True)

    p_kill = sub.add_parser("kill-managed", help="Terminate only an exact managed browser PID proven by diagnostic evidence")
    p_kill.add_argument("--diagnostic", type=Path, required=True)
    p_kill.add_argument("--pid", type=int, required=True)
    p_kill.add_argument("--confirm-pid", action="store_true")

    p_record = sub.add_parser("record", help="Record one gate result")
    p_record.add_argument("--run-dir", type=Path, required=True)
    p_record.add_argument("--gate", required=True)
    p_record.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    p_record.add_argument("--note", default="")
    p_record.add_argument("--owner-accepted", action="store_true")
    p_record.add_argument("--evidence", action="append", default=[])

    p_run = sub.add_parser("run", help="Interactively walk/resume the gate checklist")
    p_run.add_argument("--run-dir", type=Path, required=True)

    p_summary = sub.add_parser("summary", help="Show final acceptance status")
    p_summary.add_argument("--run-dir", type=Path, required=True)

    args = parser.parse_args()
    root = repo_root()

    if args.cmd == "init":
        run_dir = init_run(root, args.evidence_root)
        print(f"PR11_RUN_DIR={run_dir}")
        env = load_json(run_dir / "environment.json")
        ok, failures = environment_pass(env)
        print("ENVIRONMENT_PREFLIGHT=" + ("PASS" if ok else "BLOCKED"))
        for failure in failures:
            print(" -", failure)
        print(f"Fixtures: {run_dir / 'fixtures'}")
        return 0 if ok else 2
    if args.cmd == "environment":
        snapshot = environment_snapshot(root)
        if args.run_dir:
            write_json_atomic(args.run_dir / "environment.json", snapshot)
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        ok, failures = environment_pass(snapshot)
        print("RESULT:", "PASS" if ok else "BLOCKED")
        for failure in failures:
            print(" -", failure)
        return 0 if ok else 2
    if args.cmd == "serve":
        serve(args.run_dir, args.host, args.port)
        return 0
    if args.cmd == "capture-browser":
        path = capture_browser(args.run_dir, args.diagnostic)
        print(f"SANITIZED_BROWSER_EVIDENCE={path}")
        return 0
    if args.cmd == "kill-managed":
        return safe_kill_from_diagnostic(args.diagnostic, args.pid, args.confirm_pid)
    if args.cmd == "record":
        record_gate(args.run_dir, args.gate, args.status, args.note, args.owner_accepted, args.evidence)
        print(f"RECORDED {args.gate}={args.status}")
        return 0
    if args.cmd == "run":
        return interactive(args.run_dir)
    if args.cmd == "summary":
        status, problems = summarize(args.run_dir)
        print(f"PR-11 EVIDENCE SUMMARY: {status}")
        for item in problems:
            print(" -", item)
        return 0 if status == "PASS" else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
