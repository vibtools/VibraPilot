# VibraPilot v1.0.6.44 — Final Release Chrome TLS Closure Replace-Ready Patch

## Official baseline

- Input: `VibraPilot_Official_v1.0.6.43_Baseline(2).zip`
- Input SHA-256: `eb3d838d9fcdd1c1597883b820942b362123d3bb47190295a1f3565f37005002`
- Baseline version: `1.0.6.43`
- GitHub main merge: `8d76720740f9d822afb7ce5bc4f04f1e2407b5e9`
- Baseline source commit: `ab148f8137c1066e497136d6246ac6f84db54024`
- Baseline tree: `1fa6033f55e59d7abcdfa1fe62a781edb4024f36`
- Target version: `1.0.6.44`

## Confirmed defect and correction

The portable Windows Chrome prerequisite downloader used Python `urllib` and reproduced `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. The default network transport now uses the existing Requests dependency with mandatory TLS verification. Automatic redirects are disabled; every redirect is validated against the exact approved `https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi` policy. Windows Authenticode trust and Google LLC publisher verification remain mandatory before execution. No insecure SSL or HTTP fallback is added.

## Production source scope

- `src/vibrapilot/chrome_installer.py` only.

Phase-1, Phase-2, workflow lifecycle/multiworkflow, Plugin API 1, schemas, licensing, power, browser profiles, settings defaults, dependencies, CI and portable packaging architecture remain unchanged.

## Verification

- baseline repository verifier: PASS
- baseline pytest: 550 passed / 6 skipped / 105 subtests
- baseline unittest: 201 OK / 6 skipped
- tests-first Chrome TLS reproduction: 3 failures before fix
- targeted Chrome gate: 25 PASS
- final repository verifier: PASS
- final pytest: 553 passed / 6 skipped / 105 subtests
- final unittest: 201 OK / 6 skipped
- compileall: PASS
- git diff check: PASS
- deleted files: 0

## Delta inventory

- Public changed/new files: 24
- Private/local `project/` files: 7
- Total Delta entries: 31
- `project/**` is local/private only and must never be staged or pushed.

## External release gates

Real Windows portable Chrome download/install acceptance and GitHub v1.0.6.44 CI/portable build remain pending external evidence.
