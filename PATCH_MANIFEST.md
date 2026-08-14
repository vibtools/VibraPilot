# VibraPilot v1.0.6.31 Phase 1 — Replace-Ready Delta Manifest

## Classification

- Official Baseline Freeze: `VibraPilot_v1.0.6.30_Baseline(1).zip`
- Baseline SHA-256: `3a7fdde038ca4c6483888bbbc0fb9fd3466252cbc83845b141b9d6055d7eaaad`
- Baseline Git commit: `c86b6faebd58be9bff61cc8fdc12c76dda49a975`
- Target version: `1.0.6.31`
- Update: `Phase 1 — Chrome-Only Runtime Foundation`
- Implementation: `IMPLEMENTED / AUTOMATED VERIFIED`
- Owner Windows acceptance: `PENDING`
- Phase 2: `NOT STARTED / NOT APPROVED`
- Build/package work: `NOT PERFORMED / DEFERRED`

## Functional changes

- Google Chrome branded channel is the only production browser engine.
- Chrome-to-Playwright-Chromium retry paths are removed.
- Persistent-profile `fallback_ephemeral` keeps Google Chrome as the engine.
- Custom executable runtime authority is neutralized.
- VibraPilot unpacked Chromium side-loading runtime is disabled.
- Chromium sandbox is mandatory.
- HTTP cache source/default migration is enabled while existing explicit routing/resource controls remain available.
- Existing settings are migrated to the v1.0.6.31 mandatory browser policy.
- Policy-conflicting advanced args (`--no-sandbox`, sandbox-disable, unpacked-extension side-load and alternate `--user-data-dir`) fail closed before launch.
- `src/vibrapilot/chrome_runtime.py` adds Windows Google Chrome discovery and fail-closed product identity validation.
- Browser Settings removes editable engine/fallback/sandbox/custom-binary/unpacked-extension controls and adds a read-only Chrome-only runtime policy/status card.
- Diagnostics add Chrome-only compliance/violation evidence.

## Preserved

- Playwright automation layer.
- VibraPilot-managed persistent `slot_N` profiles and storage/session behavior.
- Task/browser lifecycle behavior outside the approved launch-policy surface.
- downloads/uploads, workflows, Share Invite behavior, licensing, TaskRuntimeStore/workspace/report schemas.
- `.github/workflows/ci.yml`, `build.py`, `requirements.txt`, `requirements-build.txt`.

## Automated evidence

```text
compileall: PASS
Phase-1 targeted tests: 19 passed
Repository verification: PASS
Full pytest: 421 passed, 6 skipped, 113 subtests passed
Unittest: 200 OK, 6 skipped
Phase-1 source diagnostic: PASS
Windows runtime acceptance: NOT RUN in audit environment / OWNER PENDING
Frozen-surface SHA verification: PASS
```

## Delta safety

- File deletions: `0`
- Runtime `AppData`: excluded
- Logs/Reports/FailedData: excluded
- `.git`: excluded
- caches/`__pycache__`/`.pyc`: excluded
- build artifacts: excluded
- the five baseline ZIP line-ending-only working-tree differences are excluded.
- `project/` files are private/local-only and are ignored by Git; never force-add or push them.

## Apply

Extract the ZIP at the VibraPilot project root and choose **Replace All**.
After applying, run the owner Windows acceptance commands/instructions provided with the delivery before committing or pushing the feature branch.
