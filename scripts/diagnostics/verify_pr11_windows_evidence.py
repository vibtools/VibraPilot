#!/usr/bin/env python3
"""Read-only verifier for VibraPilot PR-11 Windows acceptance evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "OWNER_ACCEPTED_RESIDUAL"}
MANDATORY = {f"G{i:02d}" for i in range(1, 36)} - {"G33"}


def load(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir
    required = [run_dir / "run.json", run_dir / "environment.json", run_dir / "gates.json", run_dir / "fixtures" / "manifest.json"]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        print("PR-11 EVIDENCE VERIFY: FAIL")
        for item in missing:
            print(" - MISSING:", item)
        return 1
    try:
        run = load(run_dir / "run.json")
        gates_doc = load(run_dir / "gates.json")
    except Exception as exc:
        print("PR-11 EVIDENCE VERIFY: FAIL")
        print(" -", exc)
        return 1
    failures = []
    if run.get("target_version") != "1.0.6.28":
        failures.append("target_version is not 1.0.6.28")
    if run.get("production_source_changes") != 0:
        failures.append("run metadata does not preserve zero production source changes")
    gates = gates_doc.get("gates")
    if not isinstance(gates, dict):
        failures.append("gates.json gates is not an object")
        gates = {}
    for gate in sorted(MANDATORY | {"G33"}):
        item = gates.get(gate)
        if not isinstance(item, dict):
            failures.append(f"{gate} missing")
            continue
        status = item.get("status")
        if status not in ALLOWED:
            failures.append(f"{gate} invalid status: {status}")
            continue
        if gate in MANDATORY and status != "PASS" and status != "OWNER_ACCEPTED_RESIDUAL":
            failures.append(f"{gate} mandatory gate is {status}")
        if status == "OWNER_ACCEPTED_RESIDUAL" and item.get("owner_accepted") is not True:
            failures.append(f"{gate} residual lacks explicit owner acceptance")
    if failures:
        print("PR-11 EVIDENCE VERIFY: BLOCKED/FAIL")
        for item in failures:
            print(" -", item)
        return 2
    print("PR-11 EVIDENCE VERIFY: PASS")
    print("Target: v1.0.6.28")
    print("Mandatory gates: PASS or explicitly owner-accepted residual")
    print("Production source changes: 0")
    print("PR-12: NOT STARTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
