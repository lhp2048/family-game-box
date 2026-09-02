from __future__ import annotations

from fastapi.testclient import TestClient

from app.html_prefix import rewrite_html
from app.main import _load_version, app
from app.root_path import get_root_path

client = TestClient(app)
PREFIX = get_root_path()  # default /game-box


def p(path: str) -> str:
    if not PREFIX:
        return path
    if path == "/":
        return PREFIX + "/"
    return PREFIX + path


GAME_IDS = [
    "24points",
    "schulte",
    "stroop",
    "cancel",
    "simon",
    "spot-diff",
    "maze",
    "sudoku",
    "24points-library",
]


def test_root_path_default():
    assert PREFIX == "/game-box"


def test_health_ok():
    r = client.get(p("/api/v1/health"))
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "family_game_box"
    assert body["port"] == 18029
    assert body["status"] == "running"
    assert body["version"] == _load_version()
    assert body["rootPath"] == PREFIX


def test_health_alias_unprefixed():
    if not PREFIX:
        return
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["rootPath"] == PREFIX


def test_root_redirects_to_prefix():
    if not PREFIX:
        return
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (307, 302)
    assert r.headers["location"] == PREFIX + "/"


def test_games_catalog():
    r = client.get(p("/api/v1/games"))
    assert r.status_code == 200
    games = r.json()["games"]
    assert [g["id"] for g in games] == GAME_IDS
    assert games[0]["path"] == "/games/24points/play.html"
    assert games[2]["path"] == "/games/stroop/"
    assert games[5]["path"] == "/games/spot-diff/"
    assert games[-1]["extra"]["kind"] == "reference"


def test_schulte_page():
    r = client.get(p("/games/schulte/"))
    assert r.status_code == 200
    text = r.text
    assert "舒尔特" in text
    assert '__FGB_BASE__="/game-box"' in text
    assert 'href="/game-box/"' in text or 'href="/game-box"' in text
    assert 'src="/game-box/js/fgb-client.js"' in text


def test_lobby_html():
    r = client.get(p("/"))
    assert r.status_code == 200
    text = r.text
    assert "Stroop 色字" in text
    assert 'href="games/stroop/"' in text
    assert 'href="/game-box/leaderboard"' in text
    assert "fgb-client.js" in text
    assert "每日挑战" in text
    assert 'href="/game-box/daily"' in text
    assert 'href="/game-box/admin"' in text
    assert 'href="/game-box/daily/leaderboard"' in text
    assert '__FGB_BASE__="/game-box"' in text


def test_leaderboard_page():
    r = client.get(p("/leaderboard"))
    assert r.status_code == 200
    assert "排行榜" in r.text


def test_home_back_to_lobby():
    play = client.get(p("/games/24points/play.html")).text
    assert "← 返回大厅" in play
    assert "/game-box" in play
    schulte = client.get(p("/games/schulte/")).text
    assert "← 返回大厅" in schulte


def test_attention_game_page():
    r = client.get(p("/games/stroop/"))
    assert r.status_code == 200
    text = r.text
    assert "Stroop" in text
    assert "/game-box" in text


def test_24points_play_and_bank():
    page = client.get(p("/games/24points/play.html"))
    assert page.status_code == 200
    bank = client.get(p("/games/24points/bank.json"))
    assert bank.status_code == 200
    data = bank.json()
    assert isinstance(data, list) and len(data) > 100


def test_rewrite_html_helper():
    raw = '<head></head><a href="/">home</a><script src="/js/x.js"></script>'
    out = rewrite_html(raw, "/game-box")
    assert '__FGB_BASE__="/game-box"' in out
    assert 'href="/game-box/"' in out
    assert 'src="/game-box/js/x.js"' in out
    # no double prefix
    out2 = rewrite_html(out, "/game-box")
    assert out2.count("/game-box/game-box") == 0
