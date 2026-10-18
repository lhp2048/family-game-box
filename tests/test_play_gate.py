import time

import pytest

from app import daily_admin as da


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)


def test_cannot_enable_without_passphrase():
    with pytest.raises(ValueError):
        da.put_play_gate(True, None)


def test_unlock_and_invalidate_on_change():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    assert da.play_cookie_ok(cookie, now=now) is True
    assert da.play_cookie_ok("bad", now=now) is False
    with pytest.raises(ValueError, match="口令不对"):
        da.issue_play_cookie("nope", now=now)
    da.put_play_gate(True, "family2")
    assert da.play_cookie_ok(cookie, now=now) is False


def test_disable_keeps_generation():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    first = da._load()["playGeneration"]
    da.put_play_gate(False, None)
    assert da._load()["playGeneration"] == first
    da.put_play_gate(True, None)
    assert da._load()["playGeneration"] == first + 1
    assert da.play_cookie_ok(cookie, now=now) is False
