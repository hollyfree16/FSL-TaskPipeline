import os
import sys


# Ensure repo root is importable so tests can import `run_pipeline` and `utils`.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
