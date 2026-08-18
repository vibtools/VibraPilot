# VibraPilot v1.0.6.39 — Phase 1 Replace-Ready Patch Manifest

## Identity

- Official baseline: `v1.0.6.38`
- Baseline commit: `bc894115f505b7b9ecbc15a235b91d37a9693cec`
- Baseline tree: `8bc5cba5c2d6256769caf1e2fdd5e0a1afd53faf`
- Baseline ZIP SHA-256: `59d444b54ad1068060399bc10f418124f13ff2af797f19d6f127affa776bbe9a`
- Target: `v1.0.6.39`
- Scope ID: `VP-V10639-RUNTIME-RELIABILITY-SESSION-POLICY-001`
- State: `LOCAL VERIFIED / WINDOWS ACCEPTANCE PENDING / UNRELEASED`

## Public delta

- Changed/new public project files: **36**
- Deleted files: **0**
- Production/runtime-config files: **4**
- Test files: **12**
- Phase 2 implementation: **0 files**

## Production scope

- `src/vibrapilot/backend.py`
- `src/vibrapilot/qt_app.py`
- `src/vibrapilot/power_management.py` (new)
- `config/settings.defaults.json`

All workflow lifecycle Update/Remove/hot-switch/per-Task workflow identity work remains Phase 2 and is unchanged.

## Verification

- Historical + Phase 1 targeted regression: **120 passed**
- Full pytest: **497 passed, 6 skipped, 105 subtests passed**
- Full unittest: **201 OK, 6 skipped**
- `compileall`: **PASS**
- `scripts/verify_repository.py`: **PASS**

Target-Windows owner acceptance remains mandatory before Phase 1 is formally COMPLETE or v1.0.6.39 is published.

## Private development documentation

`project/**` is intentionally excluded from the public GitHub/release file list. Local replace-ready development delivery may carry those private governance records separately; they must never be staged/pushed.
