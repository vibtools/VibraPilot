# Getting Started

1. Install Python 3.12 x64.
2. Create/activate a virtual environment.
3. `pip install -r requirements.txt`
4. `python -m playwright install chromium`
5. Set the private Licora API key in `src/vibrapilot/backend.py`.
6. Run `python scripts/verify_repository.py`.
7. Run `python -m unittest discover -s tests -v`.
8. Launch with `python run.py`.
