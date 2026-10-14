from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app import game_registry as reg
from app.main import app
from app.root_path import get_root_path
from app.storage import DATA_DIR

client = TestClient(app)
PREFIX = get_root_path()


def p(path: str) -> str:
    if not PREFIX:
        return path
    if path == "/":
        return PREFIX + "/"
    return PREFIX + path


def _admin_token() -> str:
    # setup or login with test password in tmp data — use existing tests pattern
    st = client.get(p("/api/v1/admin/status"))
    assert st.status_code == 200
    if not st.json().get("hasPassword"):
        r = client.post(p("/api/v1/admin/setup"), json={"password": "test-admin"})
        assert r.status_code == 200
        return r.json()["token"]
    r = client.post(p("/api/v1/admin/login"), json={"password": "test-admin"})
    if r.status_code != 200:
        # password may differ in shared data dir — force unique via registry unit test only
        raise AssertionError("cannot login admin in this environment")
    return r.json()["token"]


def _make_zip(game_id: str = "hello-pack") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        manifest = {
            "id": game_id,
            "title": "Hello Pack",
            "entry": "index.html",
            "tiers": ["intro", "normal"],
            "supportsDaily": True,
            "difficultyDefaults": {
                "intro": {"label": "入门", "n": 1},
                "normal": {"label": "普通", "n": 2},
            },
            "difficultySchema": [{"key": "n", "type": "number", "label": "n"}],
        }
        zf.writestr("game.json", json.dumps(manifest, ensure_ascii=False))
        zf.writestr("index.html", "<!doctype html><title>Hello</title><h1>ok</h1>")
    return buf.getvalue()


def test_parse_game_json_ok():
    m = reg.parse_game_json(
        {"id": "foo-bar", "title": "Foo", "entry": "index.html", "supportsDaily": False}
    )
    assert m["id"] == "foo-bar"
    assert m["title"] == "Foo"


def test_install_enable_disable_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "DATA_DIR", tmp_path)
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    # re-bind upload root
    data = _make_zip("pack-demo")
    game = reg.install_zip_bytes(data)
    assert game["id"] == "pack-demo"
    assert game["enabled"] is False
    assert (tmp_path / "uploaded-games" / "pack-demo" / "index.html").is_file()
    reg.set_enabled("pack-demo", True)
    g2 = reg.get_game("pack-demo")
    assert g2 and g2["enabled"] is True
    ids = [g["id"] for g in reg.list_games()]
    assert "pack-demo" in ids
    assert any(c["id"] == "pack-demo" for c in reg.daily_candidate_games())
    reg.set_enabled("pack-demo", False)
    assert "pack-demo" not in [g["id"] for g in reg.list_games()]
    reg.delete_uploaded("pack-demo")
    assert reg.get_game("pack-demo") is None


def test_games_catalog_includes_builtins():
    r = client.get(p("/api/v1/games"))
    assert r.status_code == 200
    ids = [g["id"] for g in r.json()["games"]]
    assert "simon" in ids
    assert "stroop" in ids
    assert "24points-library" in ids


def test_games_paths_api():
    r = client.get(p("/api/v1/games/paths"))
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert paths.get("maze", "").startswith("/games/")
