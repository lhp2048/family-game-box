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
    "mental-speed",
    "number-slide",
    "huarongdao",
    "word-battle",
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
    assert 'href="/game-box/leaderboard"' in text
    assert "总排行榜" in text
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
    assert "fgb-lobby-toy" in text
    assert "fgb-lobby-toy-shell" in text
    assert "fgb-home.js" in text
    assert "fgb-toy-shelf-grid" in text
    assert "fgb-toy-top-row" in text
    assert "fgb-toy-challenges-band" in text
    assert "fgb-toy-scoreboards" in text
    assert 'id="podium-list"' in text
    assert "FGBHome.renderGameShelf" in text


def test_maze_daily_hides_new_maze_button():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/games/maze/index.html").read_text(encoding="utf-8")
    assert "fgb-daily-mode #btn-new" in html


def test_leaderboard_page():
    r = client.get(p("/leaderboard"))
    assert r.status_code == 200
    assert "排行榜" in r.text
    assert "fgb-console" in r.text
    assert "fgb-console-shell" in r.text


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
    assert "fgb-audio-clips.js" in text
    assert "FgbAudioClips" in text
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
    simon_html = (root / "web" / "games" / "simon" / "index.html").read_text(encoding="utf-8")
    assert "fgb-audio-clips.js" in simon_html
    assert "FgbAudioClips" in simon_html
    theme = (root / "web" / "css" / "fgb-theme.css").read_text(encoding="utf-8")
    for skin in expected.values():
        assert 'data-game-skin="%s"' % skin in theme, skin



def test_yuwen_and_24points_chrome():
    """Task 10: yuwen play + 24points play/library shared chrome hooks."""
    root = Path(__file__).resolve().parents[1]
    cases = [
        ("web/games/yuwen/index.html", "yuwen"),
        ("web/games/24points/play.html", "24points"),
        ("web/games/24points/library.html", "24points-library"),
    ]
    for rel, skin in cases:
        html = (root / rel).read_text(encoding="utf-8")
        assert 'data-game-skin="%s"' % skin in html, rel
        assert 'id="fgb-topbar"' in html, rel
        assert "fgb-shell.js" in html, rel
        assert "FGBShell.mountTopbar" in html, rel
        assert 'id="fgb-result"' in html, rel
    theme = (root / "web/css/fgb-theme.css").read_text(encoding="utf-8")
    for skin in ("yuwen", "24points", "24points-library"):
        assert 'data-game-skin="%s"' % skin in theme, skin


def test_stroop_challenge_stops_after_finish():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/games/stroop/index.html").read_text(encoding="utf-8")
    assert "var challengeDone = false" in html
    assert "if (challengeDone) return" in html
    assert "if (mode === \"challenge\" && challengeDone) return" in html


def test_daily_mode_hides_hint_buttons():
    root = Path(__file__).resolve().parents[1]
    theme = (root / "web/css/fgb-theme.css").read_text(encoding="utf-8")
    assert "html.fgb-daily-mode #btn-hint" in theme
    common = (root / "games/common/game_common.py").read_text(encoding="utf-8")
    assert "html.fgb-daily-mode #btn-hint" in common


def test_sudoku_numpad_touch_targets():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/games/sudoku/index.html").read_text(encoding="utf-8")
    assert "min-height: 2.75rem" in html
    assert "touch-action: manipulation" in html


def test_maze_board_centered_in_stage():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/games/maze/index.html").read_text(encoding="utf-8")
    assert "syncMazeStageLayout" in html
    assert "align-items: center" in html
    assert "justify-content: center" in html


def test_spot_diff_found_and_remain_ui():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/games/spot-diff/index.html").read_text(encoding="utf-8")
    assert 'id="remain-n"' in html
    assert "applyFoundVisual" in html
    assert "updateCounts" in html
    assert "button.found::after" in html or "button.found::after" in html


def test_cancel_board_fits_viewport():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web/games/cancel/index.html").read_text(encoding="utf-8")
    assert "var(--fgb-board" in html
    assert "scheduleCancelBoardFit" in html
    assert "overflow: hidden" in html
    assert "max-height: var(--cancel-side)" in html
    assert 'id="remain-n"' in html
    assert "updateRemainCount" in html


def test_mental_speed_page():
    login_as(client, "mental_spd")
    r = client.get(p("/games/mental-speed/"))
    assert r.status_code == 200
    text = r.text
    assert "心算" in text
    assert 'data-game-skin="mental-speed"' in text
    assert 'id="btn-start-classic"' in text
    assert 'id="ms-numpad"' in text
    assert "fgb-shell.js" in text
    assert "FGBShell.mountTopbar" in text
    assert "fgb-daily.js" in text
    assert "__FGB_IS_DAILY__" in text or "daily=1" in text


def test_mental_speed_daily_candidate():
    from app.game_registry import daily_candidate_games

    assert "mental-speed" in [g["id"] for g in daily_candidate_games()]


def test_number_slide_page():
    login_as(client, "num_slide")
    r = client.get(p("/games/number-slide/"))
    assert r.status_code == 200
    text = r.text
    assert "华容道" in text
    assert 'data-game-skin="number-slide"' in text
    assert 'id="ns-board"' in text
    assert "fgb-daily.js" in text
    assert "runWhenPlayable" in text or "FGBUI" in text


def test_number_slide_daily_candidate():
    from app.game_registry import daily_candidate_games

    assert "number-slide" in [g["id"] for g in daily_candidate_games()]


def test_huarongdao_page():
    login_as(client, "hrd_player")
    r = client.get(p("/games/huarongdao/"))
    assert r.status_code == 200
    text = r.text
    assert "华容道" in text
    assert 'data-game-skin="huarongdao"' in text
    assert 'id="hrg-board"' in text or 'class="hrg-board"' in text
    assert "hrd-solver.js" in text
    assert "fgb-shell.js" in text


def test_huarongdao_not_daily_candidate():
    from app.game_registry import daily_candidate_games

    assert "huarongdao" not in [g["id"] for g in daily_candidate_games()]


def test_word_battle_page():
    login_as(client, "word_battle")
    r = client.get(p("/games/word-battle/"))
    assert r.status_code == 200
    text = r.text
    assert "单词" in text
    assert 'data-game-skin="word-battle"' in text
    assert 'id="wb-spell"' in text
    assert "words.json" in text
    assert "FgbAudioClips" in text
    assert "audio/" in text and ".mp3" in text
    letter_a = client.get(p("/games/word-battle/audio/a.mp3"))
    assert letter_a.status_code == 200
    assert len(letter_a.content) > 400
    bank = client.get(p("/games/word-battle/words.json"))
    assert bank.status_code == 200
    data = bank.json()
    assert data.get("version") == 1
    assert len(data.get("words") or []) > 6000


def test_word_battle_not_daily_candidate():
    from app.game_registry import daily_candidate_games

    assert "word-battle" not in [g["id"] for g in daily_candidate_games()]


def test_24points_play_and_bank():
    login_as(client, "pts24_play")
    page = client.get(p("/games/24points/play.html"))
    assert page.status_code == 200
    assert 'id="card-board"' in page.text
    assert "num-card" in page.text
    assert "onPlayKeydown" in page.text or "keydown" in page.text
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
