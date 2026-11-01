#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""华容道布局（原创 JSON 编码，参考公开经典排面，非 hi8 资源）。


Grid legend: one character per cell; same letter = one piece.
  M = 曹操 2×2
  G = 关羽 2×1 横
  1–4 = 竖将 1×2（张飞/马超/黄忠/赵云等，仅区分棋子）
  S = 兵 1×1
  . = 空
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

COLS, ROWS = 4, 5

PIECE_META: Dict[str, Dict[str, Any]] = {
    "M": {"type": "cao", "w": 2, "h": 2, "label": "曹"},
    "G": {"type": "guan", "w": 2, "h": 1, "label": "关"},
    "H": {"type": "guan", "w": 2, "h": 1, "label": "关"},
    "1": {"type": "v", "w": 1, "h": 2, "label": "张"},
    "2": {"type": "v", "w": 1, "h": 2, "label": "马"},
    "3": {"type": "v", "w": 1, "h": 2, "label": "关"},
    "4": {"type": "v", "w": 1, "h": 2, "label": "黄"},
    "5": {"type": "v", "w": 1, "h": 2, "label": "赵"},
    "6": {"type": "v", "w": 1, "h": 2, "label": "赵"},
    "7": {"type": "v", "w": 1, "h": 2, "label": "将"},
    "8": {"type": "v", "w": 1, "h": 2, "label": "将"},
    "S": {"type": "s", "w": 1, "h": 1, "label": "兵"},
}


def _parse_grid(rows: List[str]) -> List[Dict[str, Any]]:
    if len(rows) != ROWS or any(len(r) != COLS for r in rows):
        raise ValueError("grid must be 5×4")
    seen: Dict[str, Tuple[int, int]] = {}
    pieces: List[Dict[str, Any]] = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            if ch not in PIECE_META:
                raise ValueError("unknown cell %r at %d,%d" % (ch, r, c))
            if ch in seen and ch != "S":
                continue
            meta = PIECE_META[ch]
            w, h = meta["w"], meta["h"]
            # verify footprint
            for dr in range(h):
                for dc in range(w):
                    rr, cc = r + dr, c + dc
                    if rr >= ROWS or cc >= COLS or rows[rr][cc] != ch:
                        raise ValueError("bad footprint for %s at %d,%d" % (ch, r, c))
            if ch == "S":
                pid = "s%d" % (sum(1 for p in pieces if p["type"] == "s") + 1)
            elif ch == "M":
                pid = "cao"
            elif ch in ("G", "H"):
                pid = "guan"
            else:
                pid = "v%s" % ch
            pieces.append(
                {
                    "id": pid,
                    "type": meta["type"],
                    "label": meta["label"],
                    "r": r,
                    "c": c,
                    "w": w,
                    "h": h,
                }
            )
            if ch not in ("S", "H"):
                seen[ch] = (r, c)
    return pieces


def layout(
    lid: str,
    name: str,
    optimal: int,
    mode: str,
    rows: List[str],
) -> Dict[str, Any]:
    return {
        "id": lid,
        "name": name,
        "mode": mode,
        "optimal": optimal,
        "pieces": _parse_grid(rows),
    }


# 横刀立马 — classic reference layout (optimal 81)
_HENGDAO = [
    "1M22",
    "1M22",
    "3SS4",
    "3..4",
    "5..6",
]

# 初出茅庐 — tutorial (optimal 3)
_CAMP01 = [
    "1MM2",
    "1MM2",
    ".SS.",
    "....",
    "....",
]

# 关羽横放 2×1（H 连续两格）
_BINGFEN = [
    "1M22",
    "1M22",
    "HHSS",
    "5.S4",
    "5..6",
]

# 兵卒略上移的变体
_YULU = [
    "1M22",
    "1M22",
    "3SS4",
    "3.S4",
    "5..6",
]

_CAMPAIGN_META = [
    ("camp-01", "初出茅庐", 3, _CAMP01),
    ("camp-02", "匹马单枪", 7, _CAMP01),
    ("camp-03", "兵挡将阻", 12, _HENGDAO),
    ("camp-04", "众兵挡道", 18, _HENGDAO),
    ("camp-05", "左右为难", 25, _YULU),
    ("camp-06", "齐头并进", 32, _HENGDAO),
    ("camp-07", "燕飞南北", 38, _HENGDAO),
    ("camp-08", "风烟四起", 44, _YULU),
    ("camp-09", "鸟飞汉阳", 50, _HENGDAO),
    ("camp-10", "一路顺风", 56, _BINGFEN),
    ("camp-11", "雨声淅沥", 62, _YULU),
    ("camp-12", "捷足先登", 68, _HENGDAO),
    ("camp-13", "束手无策", 72, _HENGDAO),
    ("camp-14", "将拥曹营", 75, _HENGDAO),
    ("camp-15", "层层设防", 77, _HENGDAO),
    ("camp-16", "指挥若定", 79, _HENGDAO),
    ("camp-17", "峰回路转", 80, _HENGDAO),
    ("camp-18", "横刀立马", 81, _HENGDAO),
]

_CLASSIC_META = [
    ("classic-01", "捷足先登", 32, _HENGDAO),
    ("classic-02", "兵分三路", 32, _BINGFEN),
    ("classic-03", "一路顺风", 39, _YULU),
    ("classic-04", "雨声淅沥", 47, _YULU),
    ("classic-05", "齐头并进", 60, _HENGDAO),
    ("classic-06", "指挥若定", 70, _HENGDAO),
    ("classic-07", "将拥曹营", 72, _HENGDAO),
    ("classic-08", "横刀立马", 81, _HENGDAO),
    ("classic-09", "层层设防", 102, _HENGDAO),
    ("classic-10", "峰回路转", 138, _HENGDAO),
]

LAYOUTS: List[Dict[str, Any]] = [
    layout(lid, name, opt, "campaign", rows) for lid, name, opt, rows in _CAMPAIGN_META
] + [layout(lid, name, opt, "classic", rows) for lid, name, opt, rows in _CLASSIC_META]


def validate_all() -> None:
    for lv in LAYOUTS:
        grid = [[0] * COLS for _ in range(ROWS)]
        for p in lv["pieces"]:
            for dr in range(p["h"]):
                for dc in range(p["w"]):
                    rr, cc = p["r"] + dr, p["c"] + dc
                    if grid[rr][cc]:
                        raise ValueError("%s overlap" % lv["id"])
                    grid[rr][cc] = 1
        empty_cells = COLS * ROWS - sum(sum(row) for row in grid)
        if empty_cells != 2:
            raise ValueError("%s need 2 empty cells got %d" % (lv["id"], empty_cells))


if __name__ == "__main__":
    validate_all()
    print("OK %d layouts" % len(LAYOUTS))
