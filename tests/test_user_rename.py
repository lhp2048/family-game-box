"""Self-service username rename."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import scores, users
from app.main import app
from helpers import login_as, url

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    yield


def test_rename_user_unit():
    from app.terminals import register_terminal

    created = users.register_user("旧名", "pass1234")
    uid = created["userId"]
    tid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    register_terminal(tid, "旧名")
    scores.submit_score(
        tid,
        "stroop",
        "challenge",
        "normal",
        {"correct": 1, "total": 1, "timeMs": 1000},
        user_id=uid,
        username="旧名",
    )
    renamed = users.rename_user(uid, "新名")
    assert renamed["username"] == "新名"
    assert renamed["userId"] == uid
    assert users.authenticate("新名", "pass1234")["userId"] == uid
    with pytest.raises(ValueError, match="口令"):
        users.authenticate("旧名", "pass1234")
    entries = [e for e in scores._load_entries() if e.get("userId") == uid]
    assert entries
    assert all(e.get("username") == "新名" for e in entries)
    assert all(e.get("nickname") == "新名" for e in entries)


def test_rename_conflict():
    a = users.register_user("alice", "pass1234")
    users.register_user("bob", "pass1234")
    with pytest.raises(ValueError, match="已占用"):
        users.rename_user(a["userId"], "Bob")


def test_rename_invalid():
    u = users.register_user("cara", "pass1234")
    with pytest.raises(ValueError, match="用户名"):
        users.rename_user(u["userId"], "")
    with pytest.raises(ValueError, match="用户名"):
        users.rename_user(u["userId"], "x" * 17)


def test_rename_api_success_and_login():
    client.cookies.clear()
    login_as(client, "renamer1")
    r = client.post(url("/api/v1/auth/rename"), json={"username": "renamer1新"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["username"] == "renamer1新"
    assert body["userId"]
    me = client.get(url("/api/v1/auth/me"))
    assert me.json()["loggedIn"] is True
    assert me.json()["username"] == "renamer1新"

    client.cookies.clear()
    bad = client.post(
        url("/api/v1/auth/login"),
        json={"username": "renamer1", "password": "pass1234"},
    )
    assert bad.status_code == 400
    ok = client.post(
        url("/api/v1/auth/login"),
        json={"username": "renamer1新", "password": "pass1234"},
    )
    assert ok.status_code == 200
    assert ok.json()["username"] == "renamer1新"


def test_rename_api_conflict():
    client.cookies.clear()
    login_as(client, "takenA")
    client.cookies.clear()
    login_as(client, "takenB")
    r = client.post(url("/api/v1/auth/rename"), json={"username": "takenA"})
    assert r.status_code == 400
    assert "占用" in r.json()["detail"]


def test_rename_api_unauthenticated():
    client.cookies.clear()
    r = client.post(url("/api/v1/auth/rename"), json={"username": "nobody"})
    assert r.status_code == 401


def test_rename_same_casefold_ok():
    """Owner may keep casefold-identical name (e.g. display tweak)."""
    u = users.register_user("Ada", "pass1234")
    out = users.rename_user(u["userId"], "ada")
    assert out["username"] == "ada"
    assert users.authenticate("ada", "pass1234")["userId"] == u["userId"]
