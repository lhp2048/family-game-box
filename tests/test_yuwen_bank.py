"""语文大擂台：题库可解析，页面和记分档位接得上。"""

from __future__ import annotations

import importlib.util
import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from helpers import login_as, url
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "web" / "games" / "yuwen" / "questions.json"
PARSER_PATH = ROOT / "games" / "yuwen" / "parse_bank.py"

client = TestClient(app)


def _parser():
    spec = importlib.util.spec_from_file_location("yuwen_parse_bank", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bank_json_matches_parser():
    module = _parser()
    parsed = module.parse_bank(module.BANK_PATH.read_text(encoding="utf-8"))
    saved = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert [q["id"] for q in parsed["questions"]] == list(range(1, 1001))
    assert [q["id"] for q in saved["questions"]] == [q["id"] for q in parsed["questions"]]
    assert [s["id"] for s in saved["stages"]] == [s["id"] for s in parsed["stages"]]
    for question in saved["questions"]:
        assert question["answer"] in ("A", "B", "C", "D")
        assert list(question["options"]) == ["A", "B", "C", "D"]
        assert all(question["options"][k] for k in "ABCD")
    zixing = next(s for s in saved["stages"] if s["id"] == "zixing")
    assert zixing["rhythm"] == "mixed"
    assert len(zixing["groups"]) == 7
    wenyan = next(s for s in saved["stages"] if s["id"] == "wenyan-read")
    assert wenyan["rhythm"] == "passage"
    assert wenyan["flashCount"] == 0


def test_hot_mark_highlights_annotated_character():
    module = _parser()
    parsed = module.parse_bank(module.BANK_PATH.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in parsed["questions"]}
    assert '<em class="yuwen-mark">叨</em>扰（dāo）' in by_id[147]["options"]["A"]
    assert '<em class="yuwen-mark">唠</em>叨（láo）' in by_id[147]["options"]["D"]
    assert "yuwen-mark" in by_id[56]["stem"]
    assert "说" in by_id[56]["stem"]
    assert "勉<em class=\"yuwen-mark\">强</em>" in by_id[111]["stem"]
    assert "<em class=\"yuwen-mark\">不刊之论</em>" in by_id[288]["options"]["A"]
    assert "<em class=\"yuwen-mark\">逮</em>" in by_id[853]["options"]["A"]


def test_yuwen_page_and_score():
    login_as(client, "yuwen_bank")
    page = client.get(url("/games/yuwen/"))
    assert page.status_code == 200
    assert "语文大擂台" in page.text
    assert "← 返回大厅" in page.text
    bank = client.get(url("/games/yuwen/questions.json"))
    assert bank.status_code == 200
    assert bank.json()["questions"][0]["id"] == 1

    catalog = client.get(url("/api/v1/games")).json()["games"]
    game = next(g for g in catalog if g["id"] == "yuwen")
    saved = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert game["tiers"] == [s["id"] for s in saved["stages"]]
    assert game["title"] == "语文大擂台"

    terminal = str(uuid.uuid4())
    headers = {"X-Terminal-Id": terminal}
    reg = client.post(
        url("/api/v1/terminals/register"),
        json={"terminalId": terminal, "nickname": "语文选手"},
    )
    assert reg.status_code == 200
    submitted = client.post(
        url("/api/v1/scores"),
        headers=headers,
        json={
            "gameId": "yuwen",
            "mode": "challenge",
            "tier": "zuyin",
            "tierLabel": "字音",
            "display": "8/10 · 01:12",
            "metrics": {"correct": 8, "total": 10, "timeMs": 72000},
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["entry"]["tierLabel"] == "字音"
    board = client.get(url("/api/v1/leaderboard"), params={
        "gameId": "yuwen",
        "mode": "challenge",
        "tier": "zuyin",
    })
    assert board.status_code == 200
    assert board.json()["tierLabel"] == "字音"
    mine = [item for item in board.json()["items"] if item.get("terminalId") == terminal]
    assert mine and "8/10" in mine[0]["display"]
