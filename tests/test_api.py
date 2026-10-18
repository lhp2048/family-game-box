from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.html_prefix import rewrite_html
from app.main import _load_version, app
from app.root_path import get_root_path
from helpers import login_as

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
    "yuwen",
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
    login_as(client, "schulte_pg")
    r = client.get(p("/games/schulte/"))
    assert r.status_code == 200
    text = r.text
    assert "舒尔特" in text
    assert '__FGB_BASE__="/game-box"' in text
    assert 'href="/game-box/"' in text or 'href="/game-box"' in text
    assert 'src="/game-box/js/fgb-client.js"' in text
    # Task 7 shared game chrome hooks
    assert 'data-game-skin="schulte"' in text
    assert 'id="fgb-topbar"' in text
    assert 'id="fgb-result"' in text
    assert 'id="fgb-result-retry"' in text
    assert 'id="fgb-result-hall"' in text
    assert 'id="fgb-result-board"' in text
    assert "fgb-shell.js" in text
    assert "FGBShell.mountTopbar" in text
    # Existing in-page result + score submit path unchanged
    assert 'id="view-result"' in text
    assert "fgbSubmitScore" in text


def test_lobby_html():
    r = client.get(p("/"))
    assert r.status_code == 200
    text = r.text
    assert 'id="game-list"' in text
    assert "/api/v1/games" in text
    # Free-train board link lives in shell top-nav JS (FGB.url), not a static href
    assert 'href: "/leaderboard"' in text or 'href="/game-box/leaderboard"' in text
    assert "fgb-client.js" in text
    assert "fgb-shell.js" in text
    assert "FGBShell.mountTopbar" in text
    assert "每日专注力挑战" in text
    assert "每日语文挑战" in text
    assert 'href="/game-box/yuwen-daily"' in text
    assert 'href="/game-box/yuwen-daily/leaderboard"' in text
    assert 'href="/game-box/daily"' in text
    assert 'href="/game-box/admin"' in text
    assert 'href="/game-box/daily/leaderboard"' in text
    assert '__FGB_BASE__="/game-box"' in text


def test_leaderboard_page():
    r = client.get(p("/leaderboard"))
    assert r.status_code == 200
    assert "排行榜" in r.text


def test_build_packs_shell_pages():
    root = Path(__file__).resolve().parents[1]
    shell = (root / "scripts" / "build.sh").read_text(encoding="utf-8")
    bat = (root / "scripts" / "build.bat").read_text(encoding="utf-8")
    assert 'web/"*.html' in shell
    assert "web\\*.html" in bat
    assert "web/css" in shell
    required = [
        "yuwen-daily.html",
        "yuwen-daily-leaderboard.html",
        "daily.html",
        "daily-leaderboard.html",
    ]
    for name in required:
        assert (root / "web" / name).is_file()


def test_home_back_to_lobby():
    login_as(client, "home_back")
    play = client.get(p("/games/24points/play.html")).text
    assert "← 返回大厅" in play
    assert "/game-box" in play
    schulte = client.get(p("/games/schulte/")).text
    assert "← 返回大厅" in schulte


def test_attention_game_page():
    login_as(client, "attn_game")
    r = client.get(p("/games/stroop/"))
    assert r.status_code == 200
    text = r.text
    assert "Stroop" in text
    assert "/game-box" in text
    # Task 8 pilot skin + shared chrome
    assert 'data-game-skin="stroop"' in text
    assert 'id="fgb-topbar"' in text
    assert "fgb-shell.js" in text
    assert "FGBShell.mountTopbar" in text
    assert "fgbSubmitScore" in text or "submitScore" in text or "view-result" in text



def test_remaining_free_train_chrome():
    """Task 9: cancel/simon/spot-diff/maze/sudoku share chrome + skin hooks."""
    root = Path(__file__).resolve().parents[1]
    expected = {
        "cancel": "cancel",
        "simon": "simon",
        "spot-diff": "spot-diff",
        "maze": "maze",
        "sudoku": "sudoku",
    }
    for slug, skin in expected.items():
        html = (root / "web" / "games" / slug / "index.html").read_text(encoding="utf-8")
        assert 'data-game-skin="%s"' % skin in html, slug
        assert 'id="fgb-topbar"' in html, slug
        assert 'id="fgb-result"' in html, slug
        assert "fgb-shell.js" in html, slug
        assert "FGBShell.mountTopbar" in html, slug
        assert "← 返回大厅" in html or "回大厅" in html, slug
    theme = (root / "web" / "css" / "fgb-theme.css").read_text(encoding="utf-8")
    for skin in expected.values():
        assert 'data-game-skin="%s"' % skin in theme, skin


def test_24points_play_and_bank():
    login_as(client, "pts24_play")
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
