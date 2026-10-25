#!/usr/bin/env node
/* eslint-disable no-console */
"use strict";

const fs = require("fs");
const path = require("path");
const Klotski = require("./klotski-ref.js");

const HRD = JSON.parse(
  fs.readFileSync(path.join(__dirname, "hrd-games.json"), "utf8")
);

const ESCAPE_ROW = 3;
const ESCAPE_COL = 1;

function macroCount(moves) {
  if (!moves || !moves.length) return 0;
  let macro = 0;
  let last = -1;
  for (const m of moves) {
    if (m.blockIdx !== last) macro += 1;
    last = m.blockIdx;
  }
  return macro;
}

const V_GENERAL_LABELS = ["张", "赵", "马", "黄"];

function blocksToPieces(blocks) {
  const pieces = [];
  let v = 0;
  let hBar = 0;
  blocks.forEach((b, i) => {
    const h = b.shape[0];
    const w = b.shape[1];
    const [r, c] = b.position;
    let type = "s";
    let label = "兵";
    if (w === 2 && h === 2) {
      type = "cao";
      label = "曹";
    } else if (w === 1 && h === 2) {
      v += 1;
      type = "v";
      label = V_GENERAL_LABELS[(v - 1) % V_GENERAL_LABELS.length];
    } else if (w === 2 && h === 1) {
      hBar += 1;
      if (hBar === 1) {
        type = "guan";
        label = "关";
      } else {
        type = "h";
        label = "横";
      }
    }
    pieces.push({
      id: type === "cao" ? "cao" : type + i,
      type,
      label,
      r,
      c,
      w,
      h,
    });
  });
  return pieces;
}

function cloneBlocks(blocks) {
  return blocks.map((b) => ({
    shape: b.shape.slice(),
    position: b.position.slice(),
  }));
}

function applyMove(blocks, move) {
  const b = blocks[move.blockIdx];
  const dir = [
    [1, 0],
    [0, 1],
    [-1, 0],
    [0, -1],
  ][move.dirIdx];
  const next = cloneBlocks(blocks);
  next[move.blockIdx].position = [
    b.position[0] + dir[0],
    b.position[1] + dir[1],
  ];
  return next;
}

function replayStates(startBlocks, moves) {
  const states = [cloneBlocks(startBlocks)];
  let cur = cloneBlocks(startBlocks);
  for (const m of moves) {
    cur = applyMove(cur, m);
    states.push(cloneBlocks(cur));
  }
  return states;
}

function suffixMacro(moves, fromIdx) {
  return macroCount(moves.slice(fromIdx));
}

function findByName(name) {
  return HRD.find((g) => g.name === name);
}

const CLASSIC_TARGETS = [
  { id: "classic-01", name: "捷足先登", optimal: 32, candidates: ["捷足先登"] },
  {
    id: "classic-02",
    name: "兵分三路",
    optimal: 73,
    candidates: ["并分三路", "兵分三路", "四路进兵"],
  },
  { id: "classic-03", name: "一路顺风", optimal: 39, candidates: ["一路顺风"] },
  { id: "classic-04", name: "雨声淅沥", optimal: 47, candidates: ["雨声淅沥"] },
  { id: "classic-05", name: "齐头并进", optimal: 60, candidates: ["齐头并进"] },
  { id: "classic-06", name: "指挥若定", optimal: 70, candidates: ["指挥若定"] },
  { id: "classic-07", name: "将拥曹营", optimal: 72, candidates: ["将拥曹营", "兵临曹营"] },
  { id: "classic-08", name: "横刀立马", optimal: 81, candidates: ["横刀立马"] },
  { id: "classic-09", name: "层层设防", optimal: 102, candidates: ["层层设防"] },
  { id: "classic-10", name: "峰回路转", optimal: 138, candidates: ["峰回路转"] },
];

const CAMPAIGN_META = [
  { id: "camp-01", name: "初出茅庐", optimal: 3 },
  { id: "camp-02", name: "匹马单枪", optimal: 7 },
  { id: "camp-03", name: "兵挡将阻", optimal: 12 },
  { id: "camp-04", name: "众兵挡道", optimal: 18 },
  { id: "camp-05", name: "左右为难", optimal: 25 },
  { id: "camp-06", name: "齐头并进", optimal: 32 },
  { id: "camp-07", name: "燕飞南北", optimal: 38 },
  { id: "camp-08", name: "风烟四起", optimal: 44 },
  { id: "camp-09", name: "鸟飞汉阳", optimal: 50 },
  { id: "camp-10", name: "一路顺风", optimal: 56 },
  { id: "camp-11", name: "雨声淅沥", optimal: 62 },
  { id: "camp-12", name: "捷足先登", optimal: 68 },
  { id: "camp-13", name: "束手无策", optimal: 72 },
  { id: "camp-14", name: "将拥曹营", optimal: 75 },
  { id: "camp-15", name: "层层设防", optimal: 77 },
  { id: "camp-16", name: "指挥若定", optimal: 79 },
  { id: "camp-17", name: "峰回路转", optimal: 80 },
  { id: "camp-18", name: "横刀立马", optimal: 81 },
];

function solveGame(blocks) {
  const k = new Klotski();
  const moves = k.solve({ blocks: cloneBlocks(blocks) });
  if (!moves) return null;
  // klotski returns win → start; replay needs start → win
  return moves.slice().reverse();
}

function pickClassic(entry) {
  let best = null;
  for (const cand of entry.candidates) {
    const g = findByName(cand);
    if (!g) continue;
    const moves = solveGame(g.blocks);
    if (!moves) continue;
    const macro = macroCount(moves);
    const diff = Math.abs(macro - entry.optimal);
    const item = { g, moves, macro, diff, cand };
    if (!best || diff < best.diff) best = item;
  }
  return best;
}

function layoutFromBlocks(id, name, mode, optimal, blocks, verifiedMacro) {
  return {
    id,
    name,
    mode,
    optimal,
    verifiedMacro,
    pieces: blocksToPieces(blocks),
  };
}

function buildCampaignFromHengdao() {
  const heng = findByName("横刀立马");
  const moves = solveGame(heng.blocks);
  if (!moves) throw new Error("cannot solve hengdao");
  const states = replayStates(heng.blocks, moves);
  const layouts = [];
  for (let i = 0; i < 10; i++) {
    const meta = CAMPAIGN_META[i];
    let pickIdx = 0;
    let bestDiff = Infinity;
    for (let s = 0; s < states.length; s++) {
      const rem = suffixMacro(moves, s);
      const diff = Math.abs(rem - meta.optimal);
      if (diff < bestDiff) {
        bestDiff = diff;
        pickIdx = s;
      }
    }
    layouts.push(
      layoutFromBlocks(
        meta.id,
        meta.name,
        "campaign",
        meta.optimal,
        states[pickIdx],
        suffixMacro(moves, pickIdx)
      )
    );
  }
  return layouts;
}

function main() {
  const classic = [];
  const notes = [];
  for (const entry of CLASSIC_TARGETS) {
    const pick = pickClassic(entry);
    if (!pick) {
      throw new Error("no layout for " + entry.name);
    }
    const useOptimal = pick.macro;
    if (pick.macro !== entry.optimal) {
      notes.push(
        entry.name +
          ": catalog " +
          entry.optimal +
          ", verified macro " +
          pick.macro +
          " (" +
          pick.cand +
          ")"
      );
    }
    classic.push(
      layoutFromBlocks(
        entry.id,
        entry.name,
        "classic",
        useOptimal,
        pick.g.blocks,
        pick.macro
      )
    );
  }

  const campaignEarly = buildCampaignFromHengdao();
  const campaignLate = [];
  for (let i = 10; i < CAMPAIGN_META.length; i++) {
    const meta = CAMPAIGN_META[i];
    const pick = pickClassic({
      id: meta.id,
      name: meta.name,
      optimal: meta.optimal,
      candidates: [meta.name, "横刀立马", "指挥若定", "将拥曹营"],
    });
    if (!pick) throw new Error("campaign late " + meta.name);
    campaignLate.push(
      layoutFromBlocks(
        meta.id,
        meta.name,
        "campaign",
        meta.optimal,
        pick.g.blocks,
        pick.macro
      )
    );
  }

  const out = {
    version: 1,
    board: { rows: 5, cols: 4 },
    escape: { row: ESCAPE_ROW, col: ESCAPE_COL },
    source: "jeantimex/klotski hrd-games.json (MIT)",
    notes,
    layouts: [...campaignEarly, ...campaignLate, ...classic],
  };

  const outPath = path.join(__dirname, "layouts.json");
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2), "utf8");
  console.log("Wrote", outPath, "layouts", out.layouts.length);
  if (notes.length) console.warn("Notes:\n" + notes.join("\n"));
}

main();
