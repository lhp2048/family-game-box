from __future__ import annotations

import uuid

import pytest

from app.storage import load_json, save_json, storage_backend


def test_file_backend_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    assert storage_backend() == "file"
    assert load_json("scores.json", {"version": 1, "entries": []}) == {
        "version": 1,
        "entries": [],
    }
    save_json("scores.json", {"version": 1, "entries": [{"id": "a"}]})
    assert load_json("scores.json", {})["entries"][0]["id"] == "a"
    text = (tmp_path / "scores.json").read_text(encoding="utf-8")
    assert text.endswith("\n")


def test_incomplete_turso_env_raises(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://example.turso.io")
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    assert storage_backend() == "incomplete"
    with pytest.raises(RuntimeError, match="TURSO_DATABASE_URL"):
        load_json("scores.json", {})
    with pytest.raises(RuntimeError, match="TURSO_AUTH_TOKEN"):
        save_json("scores.json", {"version": 1})


def test_turso_roundtrip_does_not_write_files(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    files = tmp_path / "files"
    monkeypatch.setenv("TURSO_DATABASE_URL", str(db_path))
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr("app.storage.DATA_DIR", files)

    assert storage_backend() == "turso"
    assert load_json("scores.json", {"version": 1, "entries": []}) == {
        "version": 1,
        "entries": [],
    }
    save_json("scores.json", {"version": 1, "entries": [{"id": "甲"}]})
    assert load_json("scores.json", {})["entries"] == [{"id": "甲"}]
    assert not (files / "scores.json").exists()

    import libsql

    conn = libsql.connect(str(db_path))
    row = conn.execute("SELECT doc FROM kv WHERE name = ?", ("scores.json",)).fetchone()
    assert row is not None
    assert "甲" in row[0]
    conn.close()


def test_turso_invalid_document_returns_default(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("TURSO_DATABASE_URL", str(db_path))
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    save_json("scores.json", {"version": 1})

    import libsql

    from app.storage import reset_backend_cache

    reset_backend_cache()
    conn = libsql.connect(str(db_path))
    conn.execute("UPDATE kv SET doc = ? WHERE name = ?", ("[", "scores.json"))
    conn.commit()
    conn.close()
    reset_backend_cache()
    assert load_json("scores.json", {"version": 1, "entries": []}) == {
        "version": 1,
        "entries": [],
    }


def test_score_and_terminal_call_sites_persist_in_turso(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("TURSO_DATABASE_URL", str(db_path))
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path / "files")

    from app.scores import submit_score
    from app.terminals import register_terminal

    tid = str(uuid.uuid4())
    register_terminal(tid, "玩家")
    submit_score(
        tid,
        "stroop",
        "challenge",
        "normal",
        {"correct": 20, "total": 20, "timeMs": 40000},
    )

    import libsql

    conn = libsql.connect(str(db_path))
    names = {row[0] for row in conn.execute("SELECT name FROM kv").fetchall()}
    conn.close()
    assert names == {"terminals.json", "scores.json"}
    assert not (tmp_path / "files").exists()
