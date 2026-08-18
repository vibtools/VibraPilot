# VibraPilot v1.0.6.41 — Phase 1 Active-Page Origin Closure Replace-Ready Patch

## Baseline identity

- Official input: `VibraPilot_Official_v1.0.6.40_Baseline(1).zip`
- Input SHA-256: `b66cd21c1233761dbc6584f173c28017632f795bf16e98afc7eb1ffb2e2e6ad0`
- Version: `1.0.6.40`
- Git branch: `main`
- Git commit: `7e6f4cc7abf49e08d4a94124ebffa97bb7794137`
- Git tree: `8b8b6f8e502011d730ac4508300c25273e3dbab5`
- Uploaded workspace note: five tracked files differ only by line endings; semantic `git diff --ignore-space-at-eol` is empty.

## Confirmed finding

`AutomationWorker._origin_from_url()` returned `None` for an omitted port but `443`/`80` for the browser-equivalent explicit default port. In a restored multi-tab context, `_select_preferred_page()` could therefore fail target-origin matching and choose an unrelated last usable tab.

## Production correction scope

- `src/vibrapilot/backend.py`
- Method: `AutomationWorker._origin_from_url`
- Default HTTPS `:443` → canonical omitted/default representation
- Default HTTP `:80` → canonical omitted/default representation
- Non-default ports remain significant
- Malformed-port fail-safe remains unchanged

## Frozen scope

No changes are authorized to Qt UI/UX, Windows power implementation, browser settings, workflows/plugin lifecycle, licensing, persistence schemas, dependencies, CI, portable-release architecture or Phase 2 features.

## Verification state

- Tests-first reproduction: **2 FAILED / 2 PASSED** before the fix.
- Targeted correction regression: **17 PASSED**.
- Complete Phase-1 work-package gate: **28 PASSED**.
- Metadata/scope integration: **8 PASSED** + repository verifier **PASS**.
- Final full pytest: **510 passed, 6 skipped, 105 subtests passed**.
- Final unittest: **201 OK, 6 skipped**.
- compileall: **PASS**.
- Public changed/new files: **23**.
- Private `project/` changed/new files: **13**.
- Total replace-ready delta entries: **36**.
- Deleted files: **0**.
- Delta-apply sealing: recorded after package construction.

## Phase 2

**NOT STARTED.** Planned version moves from v1.0.6.41 to v1.0.6.42 because v1.0.6.41 is consumed by this forensic seal.

## Private development documentation

`project/**` remains local/private, is ignored by Git, and must never be staged or pushed.
