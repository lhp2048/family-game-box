"""The FastAPI preset must own the function config.

Vercel only treats a ``functions`` key as a framework entrypoint when the
project framework is FastAPI. Otherwise the key is checked against files in
``api/``, and ``index.py`` fails with unused_function before the build starts.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_json_selects_fastapi_and_the_root_entrypoint():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert config["framework"] == "fastapi"
    assert set(config["functions"]) == {"index.py"}
    assert config["functions"]["index.py"]["maxDuration"] == 30

    entry = ROOT / "index.py"
    assert entry.is_file()
    source = entry.read_text(encoding="utf-8")
    assert "from app.main import app" in source

    app_main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "\napp = create_app()\n" in app_main
    assert (ROOT / "web" / "index.html").is_file()
    assert (ROOT / "family-product.json").is_file()
