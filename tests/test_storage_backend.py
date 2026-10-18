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
