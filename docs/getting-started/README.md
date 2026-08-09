# Getting Started

1. Install Python 3.12 x64 on Windows 10/11.
2. Create and activate a virtual environment.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python -m playwright install chromium`.
5. Do **not** add a Licora API v1 shared/master key. Secure licensing public configuration and the pinned server RSA public key are already defined in `config/AppConfig/licensing_public.py`.
6. Run `python scripts/verify_repository.py`.
7. Run `python -m pytest -q`.
8. For the standard-library suite in PowerShell, run `$env:PYTHONPATH = "$PWD\src"` and then `python -m unittest discover -s tests -p "test_*.py" -v`.
9. Launch with `python run.py`.

On first successful Secure API v2 activation, VibraPilot creates and persistently protects a P-256 device key through Windows DPAPI. Existing protected pre-v2 license caches are restored through the existing activation shell and migrated only after successful API v2 server validation.
