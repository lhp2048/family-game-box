import pytest

from app import daily_challenges as dc


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_ensure_today_stable_same_day():
    a = dc.ensure_today()
    b = dc.ensure_today()
    assert a["comboId"] == b["comboId"]
    assert a["date"] == dc.local_today()
    assert len(a["stages"]) == 8
    assert all("seed" in s for s in a["stages"])


def test_regenerate_archives_and_keeps_history_cap(monkeypatch):
    first = dc.ensure_today()
    second = dc.regenerate()
    assert first["comboId"] != second["comboId"]
    hist = dc.get_history()
    assert len(hist) == 1
    assert hist[0]["comboId"] == first["comboId"]
    for _ in range(25):
        dc.regenerate()
    assert len(dc.get_history()) == 20


def test_cross_day_rolls(monkeypatch):
    c1 = dc.ensure_today()
    monkeypatch.setattr(dc, "local_today", lambda: "2099-01-02")
    c2 = dc.ensure_today()
    assert c2["date"] == "2099-01-02"
    assert c1["comboId"] in [h["comboId"] for h in dc.get_history()]
