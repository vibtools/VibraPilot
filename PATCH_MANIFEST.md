# VibraPilot v1.0.6.42 — Phase 2 Replace-Ready Patch

## Baseline identity

- Official input: `VibraPilot_Official_v1.0.6.41_Baseline(1).zip`
- Input SHA-256: `9296626e20076a5ded1a2c6b854ce25489b09be9d8fb204061eba14612642982`
- Baseline version: `1.0.6.41`
- Baseline Git commit: `615fe1148431b90334e9ff3f9ae02b37a36bd1d8`
- Baseline Git tree: `a6cb42814d7ed993ff5961823cf681e0cb0c0252`
- Target version: `1.0.6.42`

## Scope

- strict-newer Workflow Update/Replace with staged validation, rollback and crash recovery;
- Workflow Remove/Unload and default Deactivate;
- restart-free normal activation/switch/lifecycle;
- immutable per-Task workflow identity and simultaneous different-workflow Tasks;
- workspace/runtime schema-v2 workflow provenance;
- workflow-aware Reports and per-workflow Dashboard metrics;
- existing Chrome prerequisite/secure-install source re-verified byte-frozen.

## Frozen boundaries

Plugin API 1, Chrome prerequisite implementation, browser profile architecture, power management, licensing, runtime settings defaults, dependencies, CI and portable packaging are unchanged.

## Automated verification

- repository verifier: **PASS**
- full pytest: **541 passed, 6 skipped, 105 subtests passed**
- full unittest: **201 OK, 6 skipped**
- compileall: **PASS**
- `git diff --check`: **PASS**
- deleted files: **0**

## Replace-ready inventory

- Public changed/new files: **48**
- Private/local `project/` files: **20**
- Total Delta entries: **68**
- `project/**` is private/local only and must never be staged or pushed.

Windows live acceptance and GitHub v1.0.6.42 CI remain pending external evidence.
