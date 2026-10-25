from __future__ import annotations

import json
import subprocess
from pathlib import Path

LAYOUTS = Path(__file__).resolve().parents[1] / "games" / "huarongdao" / "layouts.json"
HRD_DIR = LAYOUTS.parent

CLASSIC_TYPES = {
    "classic-08": "24422442233221121001",
    "classic-01": "14411441033022222222",
}

CLASSIC_OPTIMA = {
    "classic-01": 32,
    "classic-02": 73,
    "classic-03": 39,
    "classic-04": 47,
    "classic-05": 60,
    "classic-06": 70,
    "classic-07": 72,
    "classic-08": 81,
    "classic-09": 102,
    "classic-10": 138,
}


def _audit_node() -> dict:
    script = r"""
const L = require('./layouts.json');
const { validateJeantimexBlocks, typeFromJeantimexBlocks } = require('./hrd_codec.js');
const Klotski = require('./klotski-ref.js');
function macro(moves) {
  let n=0,last=-1;
  for (const m of moves) { if (m.blockIdx!==last) n++; last=m.blockIdx; }
  return n;
}
const k = new Klotski();
const errors = [];
for (const lv of L.layouts) {
  const blocks = lv.pieces.map(p=>({shape:[p.h,p.w],position:[p.r,p.c]}));
  try { validateJeantimexBlocks(blocks); } catch (e) { errors.push(lv.id+': validate '+e.message); continue; }
  const t = typeFromJeantimexBlocks(blocks);
  if (t !== lv.type) errors.push(lv.id+': type mismatch');
  const moves = k.solve({blocks: JSON.parse(JSON.stringify(blocks))});
  const mac = moves ? macro(moves) : -1;
  if (mac !== lv.optimal) errors.push(lv.id+': macro '+mac+' != '+lv.optimal);
}
console.log(JSON.stringify({errors, count: L.layouts.length}));
"""
    out = subprocess.check_output(
        ["node", "-e", script],
        cwd=str(HRD_DIR),
        text=True,
    )
    return json.loads(out.strip())


def test_huarongdao_layouts_node_audit_clean():
    result = _audit_node()
    assert result["count"] == 28
    assert result["errors"] == []


def test_huarongdao_piece_labels_and_win_escape():
    data = json.loads(LAYOUTS.read_text(encoding="utf-8"))
    assert data["escape"] == {"row": 3, "col": 1}
    for lv in data["layouts"]:
        pieces = lv["pieces"]
        assert pieces[0]["type"] == "cao" and pieces[0]["label"] == "曹"
        guan = [p for p in pieces if p.get("label") == "关"]
        assert len(guan) == 1, "%s has %d 关" % (lv["id"], len(guan))
        assert guan[0].get("type") == "guan"
        vert = [p["label"] for p in pieces if p.get("type") == "v"]
        assert 1 <= len(vert) <= 4
        assert len(set(vert)) == len(vert)
        assert all(lab in {"张", "赵", "马", "黄"} for lab in vert)
        soldiers = [p for p in pieces if p.get("type") == "s"]
        assert len(soldiers) == 4
        assert lv.get("type") and len(lv["type"]) == 20
        assert lv["optimal"] == lv.get("verifiedMacro")


def test_huarongdao_classic_catalog_types_and_optima():
    data = json.loads(LAYOUTS.read_text(encoding="utf-8"))
    by_id = {lv["id"]: lv for lv in data["layouts"] if lv["mode"] == "classic"}
    for cid, opt in CLASSIC_OPTIMA.items():
        assert by_id[cid]["optimal"] == opt
    for cid, typ in CLASSIC_TYPES.items():
        assert by_id[cid]["type"] == typ


def test_huarongdao_campaign_late_are_named_boards():
    data = json.loads(LAYOUTS.read_text(encoding="utf-8"))
    camp12 = next(x for x in data["layouts"] if x["id"] == "camp-12")
    classic01 = next(x for x in data["layouts"] if x["id"] == "classic-01")
    assert camp12["name"] == "捷足先登"
    assert camp12["type"] == classic01["type"]
    assert camp12["optimal"] == 32
