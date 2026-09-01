import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_get_difficulty_public():
    r = client.get("/api/v1/difficulty")
    assert r.status_code == 200
    assert "schulte" in r.json()["games"]


def test_put_requires_admin():
    r = client.put("/api/v1/admin/difficulty", json={"games": {}})
    assert r.status_code == 401


def test_put_and_reset_with_admin():
    setup = client.post("/api/v1/admin/setup", json={"password": "secret123"})
    assert setup.status_code == 200
    token = setup.json()["token"]
    ah = {"X-Admin-Token": token}
    put = client.put(
        "/api/v1/admin/difficulty",
        headers=ah,
        json={"games": {"schulte": {"tiers": {"normal": {"size": 6, "reverse": False, "label": "普通"}}}}},
    )
    assert put.status_code == 200
    assert put.json()["games"]["schulte"]["tiers"]["normal"]["size"] == 6
    reset = client.post(
        "/api/v1/admin/difficulty/reset",
        headers=ah,
        json={"gameId": "schulte"},
    )
    assert reset.status_code == 200
    assert reset.json()["games"]["schulte"]["tiers"]["normal"]["size"] == 5
