"""Root launcher for local development.

Allows running `python app.py` from the project root by delegating to
`backend/app.py`, which is the actual FastAPI entrypoint.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
BACKEND_APP = BACKEND_DIR / "app.py"


def main() -> None:
    if not BACKEND_APP.exists():
        raise FileNotFoundError(f"Backend entrypoint not found: {BACKEND_APP}")

    # Match the backend's expected import layout (`from config import ...`).
    sys.path.insert(0, str(BACKEND_DIR))
    os.chdir(BACKEND_DIR)
    runpy.run_path(str(BACKEND_APP), run_name="__main__")


if __name__ == "__main__":
    main()
