from __future__ import annotations

import json
from pathlib import Path

LAYOUTS = Path(__file__).resolve().parents[1] / "games" / "huarongdao" / "layouts.json"


def test_huarongdao_piece_labels_unique_generals():
    data = json.loads(LAYOUTS.read_text(encoding="utf-8"))
    for lv in data["layouts"]:
        pieces = lv["pieces"]
        guan_labels = [p for p in pieces if p.get("label") == "关"]
        assert len(guan_labels) == 1, "%s has %d 关 labels" % (lv["id"], len(guan_labels))
        assert guan_labels[0].get("type") == "guan"
        vert = [p["label"] for p in pieces if p.get("type") == "v"]
        assert len(vert) >= 1
        assert all(lab in {"张", "赵", "马", "黄"} for lab in vert)
        assert len(set(vert)) == len(vert)
        extras = [p["label"] for p in pieces if p.get("type") == "h"]
        assert all(lab == "横" for lab in extras)


def test_huarongdao_jiezu_pieces_in_bounds():
    data = json.loads(LAYOUTS.read_text(encoding="utf-8"))
    lv = next(x for x in data["layouts"] if x["id"] == "classic-01")
    for p in lv["pieces"]:
        assert 0 <= p["r"] and p["r"] + p["h"] <= 5
        assert 0 <= p["c"] and p["c"] + p["w"] <= 4
