# VibraPilot v1.0.6.40 — Phase 1 Forensic Closure Replace-Ready Patch

## Baseline identity

- Official input: `VibraPilot_Official_v1.0.6.39_Baseline.zip`
- SHA-256: `755c6bd4ce88be126482980dde6fd1ee5ddddaee7f7e6bd6f80fc8f96d805325`
- Version: `1.0.6.39`
- Git commit: `7bd6428a89607df34dc96fbed28d1b2ac20b9365`
- Git tree: `074780843a9f6ed62d974123339020b86353d716`
- GitHub CI run `32153560933`: SUCCESS on Windows / Python 3.12.10.

## Target

- Version: `1.0.6.40`
- Classification: Phase 1 forensic closure / corrective fix only
- Phase 2 implementation: **0 files / NOT STARTED**
- Planned Phase 2 target: `v1.0.6.41`

## Confirmed closure findings

1. System-sleep guard cleanup was not guaranteed before every fallible finalization path.
2. Required-session context recycle used the normal processing-time login short-circuit, so the claimed re-probe did not occur.
3. A failed recycle re-probe did not block the next item.
4. Malformed explicit HTTP/HTTPS ports could raise from the Phase 1 origin helper.
5. Dashboard session label did not exactly match the approved `Login Verification` wording.
6. Repository verification accepted a docstring text marker instead of validating the actual PowerRequest enum.

## Production correction scope

- `src/vibrapilot/backend.py`
- `src/vibrapilot/qt_app.py`

`src/vibrapilot/power_management.py`, `config/settings.defaults.json`, workflow/plugin lifecycle, licensing, persistence schemas, dependencies, CI and portable-release architecture are frozen from v1.0.6.39.

## Verification

- Corrective targeted tests: PASS
- Full pytest: **506 passed, 6 skipped, 105 subtests passed**
- Full unittest: **201 OK, 6 skipped**
- compileall: PASS
- repository verifier: PASS
- fresh v1.0.6.39 + Delta apply: PASS
- frozen-file SHA contract: PASS
- deletion count: **0**

Real Windows minimized/occluded 3–4 Task execution and actual OS-idle sleep prevention remain owner live-acceptance observations; they are not fabricated from unit/CI evidence.

## Payload

- Public changed/new files: **25**
- Private `project/` files: **10**
- Total delta entries: **35**
- Deletions: **0**

`project/**` is private/local only and must never be staged or pushed to GitHub.
