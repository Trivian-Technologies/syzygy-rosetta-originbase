"""
run_api.py — Local development server launcher

Changed from v3:
  - Line 9: ROOT / "main.py" → ROOT / "app.py"
  - Line 14: error message references app.py
  - Line 19: module name "syzygy_rosetta_main" → "syzygy_rosetta_app"
  - Line 28: error message references app.py
  - Line 34: "main:app" → "app:app"
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
APP_PATH = ROOT / "app.py"


def validate_app_module() -> None:
    if not APP_PATH.exists():
        raise FileNotFoundError(
            f"Expected FastAPI module at {APP_PATH}, but it was not found. "
            "Ensure app.py exists in the repository root."
        )

    spec = importlib.util.spec_from_file_location("syzygy_rosetta_app", APP_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {APP_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    app = getattr(module, "app", None)
    if app is None:
        raise AttributeError("app.py loaded, but no `app` object was found.")


if __name__ == "__main__":
    validate_app_module()
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=str(ROOT),
        reload_dirs=[str(ROOT)],
    )
