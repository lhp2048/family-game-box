import uuid

import pytest
from fastapi.testclient import TestClient

from helpers import url
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def _tid():
    return str(uuid.uuid4())


def _headers(tid):
    return {"X-Terminal-Id": tid}


def test_today_auto_generate():
    r = client.get(url("/api/v1/daily/today"))
    assert r.status_code == 200
    body = r.json()
    assert body["comboId"]
    assert len(body["stages"]) == 8


def test_start_run_requires_register():
    tid = _tid()
    r = client.post(url("/api/v1/daily/runs"), headers=_headers(tid))
    assert r.status_code == 400


def test_admin_setup_template_regenerate():
    st = client.get(url("/api/v1/admin/status")).json()
    assert st["hasPassword"] is False
    setup = client.post(url("/api/v1/admin/setup"), json={"password": "secret123"})
    assert setup.status_code == 200
    token = setup.json()["token"]
    ah = {"X-Admin-Token": token}
    put = client.put(
        url("/api/v1/admin/daily/template"),
        headers=ah,
        json={"stages": [{"gameId": "schulte", "tier": "hard"}]},
    )
    assert put.status_code == 200
    assert put.json()["stages"][0]["gameId"] == "schulte"
    first = client.get(url("/api/v1/daily/today")).json()
    regen = client.post(url("/api/v1/admin/daily/regenerate"), headers=ah)
    assert regen.status_code == 200
    assert regen.json()["comboId"] != first["comboId"]
    forbidden = client.post(url("/api/v1/admin/daily/regenerate"))
    assert forbidden.status_code == 401


def test_leaderboard_and_pages():
    r = client.get(url("/api/v1/daily/leaderboard"))
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "combos" in body
    assert client.get(url("/daily")).status_code == 200
    assert client.get(url("/daily/leaderboard")).status_code == 200
    page = client.get(url("/daily/leaderboard")).text
    assert "combo-tabs" in page
    assert client.get(url("/admin")).status_code == 200
    admin = client.get(url("/admin")).text
    assert "管理" in admin
    assert "挑战模板" in admin
    assert "重新生成今日挑战" in admin
