import json

import pytest

from app.storage import StorageError, health, load_json, save_json, turso_configured


def test_file_roundtrip(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    save_json("scores.json", {"version": 1, "entries": []})
    assert load_json("scores.json", {})["version"] == 1
    assert json.loads((tmp_path / "scores.json").read_text(encoding="utf-8"))["version"] == 1


def test_corrupt_file_returns_default(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    (tmp_path / "scores.json").write_text("{", encoding="utf-8")
    assert load_json("scores.json", {"version": 1}) == {"version": 1}


def test_vercel_without_turso_refuses_writes(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    assert turso_configured() is False
    assert health() == {"storage": "turso", "ready": False}
    with pytest.raises(StorageError):
        save_json("scores.json", {"version": 1})
    assert not (tmp_path / "scores.json").exists()


from fastapi.testclient import TestClient

from app.main import app
from helpers import url

client = TestClient(app)


def test_health_reports_file_storage(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    body = client.get(url("/api/v1/health")).json()
    assert body["status"] == "running"
    assert body["storage"] == "file"
    assert body["ready"] is True


def test_upload_rejected_when_turso_configured(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://box.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")
    response = client.post(
        url("/api/v1/admin/games/upload"),
        files={"file": ("game.zip", b"PK", "application/zip")},
        headers={"X-Admin-Token": "nope"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "请到家里的管理页上传游戏包"


def test_storage_error_returns_503(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)

    def fail_load(*_args, **_kwargs):
        raise StorageError("暂时存不上")

    monkeypatch.setattr("app.daily_admin.load_json", fail_load)
    response = client.get(url("/api/v1/admin/status"))
    assert response.status_code == 503
    assert response.json()["detail"] == "暂时存不上"
