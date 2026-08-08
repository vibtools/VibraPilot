# Public Backend and CI Verification Contract

VibraPilot keeps public documentation in `docs/` and private development material in the local, gitignored `project/` workspace.

GitHub Actions must never depend on files under `project/`.

## Backend parity

The public machine-readable parity contract is:

```text
config/verification/backend_v1.0.6_contract.json
```

It records only verification metadata derived from the private v1.0.6 developer baseline:

- core class method inventories;
- the required 54-method `AutomationWorker` inventory count;
- AST hashes for baseline classes whose implementation is frozen;
- the original top-level helper inventory;
- AST hashes for frozen helper functions.

The private source baseline itself remains under `project/` locally and is not published. When that private baseline is present during local development, `scripts/verify_repository.py` additionally cross-checks the public contract against it. In public CI, the machine contract is sufficient and no private file is required.

## Repository boundary

- `docs/`: public documentation and release/update notes.
- `project/`: private development research, plans, ADRs, source baselines and forensic working records; gitignored.
- `config/verification/`: public machine-readable verification contracts used by CI.

## CI portability

The Windows GitHub Actions job uses Node 24-native official actions (`actions/checkout@v5` and `actions/setup-python@v6`), Python 3.12, and `PYTHONPATH=<workspace>\src`.
