from fastapi.testclient import TestClient

from app.main import _load_version, app

client = TestClient(app)

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


def test_health_ok():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "family_game_box"
    assert body["port"] == 18029
    assert body["status"] == "running"
    assert body["version"] == _load_version()


def test_games_catalog():
    r = client.get("/api/v1/games")
    assert r.status_code == 200
    games = r.json()["games"]
    assert [g["id"] for g in games] == GAME_IDS
    assert games[0]["path"] == "/games/24points/play.html"
    assert games[2]["path"] == "/games/stroop/"
    assert games[5]["path"] == "/games/spot-diff/"
    assert games[-1]["extra"]["kind"] == "reference"


def test_schulte_page():
    r = client.get("/games/schulte/")
    assert r.status_code == 200
    text = r.text
    assert "舒尔特" in text
    assert "稍后再做" in text


def test_lobby_html():
    r = client.get("/")
    assert r.status_code == 200
    text = r.text
    assert "Stroop 色字" in text
    assert 'href="games/stroop/"' in text
    assert 'href="/leaderboard"' in text
    assert "fgb-client.js" in text


def test_leaderboard_page():
    r = client.get("/leaderboard")
    assert r.status_code == 200
    assert "排行榜" in r.text


def test_home_back_to_lobby():
    play = client.get("/games/24points/play.html").text
    assert "← 返回大厅" in play
    assert 'href="/"' in play
    schulte = client.get("/games/schulte/").text
    assert "← 返回大厅" in schulte


def test_attention_game_page():
    r = client.get("/games/stroop/")
    assert r.status_code == 200
    text = r.text
    assert "Stroop" in text
    assert 'href="/"' in text


def test_24points_play_and_bank():
    page = client.get("/games/24points/play.html")
    assert page.status_code == 200
    bank = client.get("/games/24points/bank.json")
    assert bank.status_code == 200
    data = bank.json()
    assert isinstance(data, list) and len(data) > 100
