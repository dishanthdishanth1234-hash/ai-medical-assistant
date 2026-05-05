"""Root launcher and ASGI export for deployment.

Supports both:
- `python app.py` for local development from the project root
- `uvicorn app:app` for platforms like Render
"""
from __future__ import annotations

import importlib.util
import os
import runpy
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
BACKEND_APP = BACKEND_DIR / "app.py"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _load_backend_module():
    spec = importlib.util.spec_from_file_location("backend_entrypoint", BACKEND_APP)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load backend entrypoint from {BACKEND_APP}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backend_module = _load_backend_module()
app = backend_module.app


def main() -> None:
    if not BACKEND_APP.exists():
        raise FileNotFoundError(f"Backend entrypoint not found: {BACKEND_APP}")

    # Match the backend's expected import layout (`from config import ...`).
    os.chdir(BACKEND_DIR)
    runpy.run_path(str(BACKEND_APP), run_name="__main__")


if __name__ == "__main__":
    main()
