#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse english-vocab-bank markdown into words.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
BANK_PATH = HERE / "bank.md"
OUT_WEB = HERE.parents[1] / "web" / "games" / "word-battle" / "words.json"
OUT_BUILD = HERE / "build" / "words.json"

LEVELS = ["primary", "junior", "senior", "ielts"]
LEVEL_HEADINGS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^##\s*一、"), "primary"),
    (re.compile(r"^##\s*二、"), "junior"),
    (re.compile(r"^##\s*三、"), "senior"),
    (re.compile(r"^##\s*四、"), "ielts"),
)

_POS_PREFIX_RE = re.compile(
    r"^(名词|形容词|及物动词|不及物动词|动词|介词|副词|连词|冠词|代词|数词|感叹词|"
    r"介词|副词|连词)\s*"
)
_TAG_RE = re.compile(r"\[[^\]]+\]")
_SHORT_POS_RE = re.compile(r"[（(]([a-z]{1,4}\.)[）)]", re.I)


def _short_pos(pos_col: str) -> str:
    text = (pos_col or "").strip()
    match = _SHORT_POS_RE.search(text)
    if match:
        return match.group(1).lower()
    return ""


def clean_gloss(raw: str) -> Tuple[str, str]:
    gloss_full = (raw or "").replace("<br>", "\n").strip()
    gloss_full = _TAG_RE.sub("", gloss_full)
    gloss_full = re.sub(r"\n{2,}", "\n", gloss_full).strip()
    head = re.split(r"<br>|,|，", gloss_full.replace("\n", "<br>"), maxsplit=1)[0]
    head = _TAG_RE.sub("", head)
    head = _POS_PREFIX_RE.sub("", head.strip())
    head = head.strip(" ，,;；")
    short = head or gloss_full.split("\n", 1)[0].strip()
    short = _POS_PREFIX_RE.sub("", short).strip()
    return short, gloss_full


def _is_playable_word(word: str) -> bool:
    w = (word or "").strip()
    if not w:
        return False
    if len(w) == 1 and w.isalpha():
        return False
    return True


def _parse_row(cells: List[str], level: str) -> Optional[Dict[str, Any]]:
    if len(cells) < 6:
        return None
    word = cells[1].strip()
    if not _is_playable_word(word):
        return None
    ipa_uk = cells[2].strip()
    ipa_us = cells[3].strip()
    pos_col = cells[4].strip()
    gloss_raw = cells[5].strip()
    gloss, gloss_full = clean_gloss(gloss_raw)
    return {
        "w": word,
        "ipa_uk": ipa_uk,
        "ipa_us": ipa_us,
        "pos": _short_pos(pos_col),
        "gloss": gloss,
        "gloss_full": gloss_full,
        "level": level,
    }


def parse_bank(text: str) -> Dict[str, Any]:
    current: Optional[str] = None
    words: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            for pattern, level_id in LEVEL_HEADINGS:
                if pattern.match(stripped):
                    current = level_id
                    break
            continue
        if current is None or not stripped.startswith("|"):
            continue
        if stripped.startswith("| ---"):
            continue
        if stripped.startswith("| 序号"):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        if parts and not parts[0]:
            parts = parts[1:]
        if parts and not parts[-1]:
            parts = parts[:-1]
        item = _parse_row(parts, current)
        if not item:
            continue
        key = item["w"].lower()
        if key in seen:
            continue
        seen.add(key)
        words.append(item)

    counts = {lvl: sum(1 for w in words if w["level"] == lvl) for lvl in LEVELS}
    return {"version": 1, "levels": LEVELS, "words": words, "counts": counts}


def write_json(data: Dict[str, Any]) -> None:
    payload = json.dumps(
        {"version": data["version"], "levels": data["levels"], "words": data["words"]},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    OUT_WEB.parent.mkdir(parents=True, exist_ok=True)
    OUT_BUILD.parent.mkdir(parents=True, exist_ok=True)
    OUT_WEB.write_text(payload, encoding="utf-8")
    OUT_BUILD.write_text(payload, encoding="utf-8")


def main() -> None:
    data = parse_bank(BANK_PATH.read_text(encoding="utf-8"))
    write_json(data)
    print(
        "words %d -> %s (counts %s)"
        % (len(data["words"]), OUT_WEB, data["counts"])
    )


if __name__ == "__main__":
    main()
