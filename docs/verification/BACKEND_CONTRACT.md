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
- canonical semantic AST hashes for baseline classes whose implementation is frozen;
- the original top-level helper inventory;
- canonical semantic AST hashes for frozen helper functions.

The private source baseline itself remains under `project/` locally and is not published. When that private baseline is present during local development, `scripts/verify_repository.py` additionally cross-checks the public contract against it. In public CI, the machine contract is sufficient and no private file is required.

## Deterministic AST hashing

The machine contract declares `ast_hash_algorithm: canonical-semantic-ast-v2`. The verifier serializes semantic AST node/field values while omitting empty or `None` optional fields before hashing. This intentionally avoids raw `ast.dump()` output because CPython minor versions can add empty fields such as `type_params`, which changes the dump text without changing program semantics.

The contract hashes are generated from the private v1.0.6 baseline. When `project/` is available locally, the verifier cross-checks both method inventories and frozen semantic hashes against that private source. Public GitHub CI uses only the machine contract.

## Repository boundary

- `docs/`: public documentation and release/update notes.
- `project/`: private development research, plans, ADRs, source baselines and forensic working records; gitignored.
- `config/verification/`: public machine-readable verification contracts used by CI.

## CI portability

The Windows GitHub Actions job uses Node 24-native official actions (`actions/checkout@v5` and `actions/setup-python@v6`), Python 3.12, and `PYTHONPATH=<workspace>\src`.
