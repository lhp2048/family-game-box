"""单词大作战：词库解析与首现分级."""

from __future__ import annotations

from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "games" / "word_battle"))
from parse_bank import clean_gloss, parse_bank  # noqa: E402

BANK = Path(__file__).resolve().parents[1] / "games" / "word_battle" / "bank.md"


def test_clean_gloss_strips_tags_and_pos():
    short, full = clean_gloss("名词 苹果, 家伙<br>[医] 苹果")
    assert short == "苹果"
    assert "[医]" not in full


def test_parse_bank_counts_first_appearance():
    assert BANK.is_file()
    data = parse_bank(BANK.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["levels"] == ["primary", "junior", "senior", "ielts"]
    counts = data["counts"]
    assert counts["primary"] >= 570
    assert counts["junior"] == 1106
    assert counts["senior"] == 2026
    assert counts["ielts"] == 2936
    assert len(data["words"]) == sum(counts.values())
    apple = next(w for w in data["words"] if w["w"] == "apple")
    assert apple["level"] == "primary"
    assert apple["gloss"]


def test_single_letter_words_filtered():
    data = parse_bank(BANK.read_text(encoding="utf-8"))
    words = {w["w"].lower() for w in data["words"]}
    assert "a" not in words
    assert "i" not in words
