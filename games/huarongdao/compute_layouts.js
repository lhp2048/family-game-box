#!/usr/bin/env node
/* eslint-disable no-console */
"use strict";

const fs = require("fs");
const path = require("path");
const Klotski = require("./klotski-ref.js");
const CLASSIC = require("./classic_catalog.js");
const {
  typeFromJeantimexBlocks,
  piecesFromJeantimexBlocks,
  validateJeantimexBlocks,
} = require("./hrd_codec.js");

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

function solveGame(blocks) {
  const k = new Klotski();
  return k.solve({ blocks: cloneBlocks(blocks) });
}

function findByName(name) {
  return HRD.filter((g) => g.name === name);
}

function pickJeantimex(entry) {
  let candidates = [];
  for (const name of entry.jeantimexNames) {
    candidates = candidates.concat(findByName(name));
  }
  if (!candidates.length) return null;

  let best = null;
  for (const g of candidates) {
    validateJeantimexBlocks(g.blocks);
    const moves = solveGame(g.blocks);
    if (!moves) continue;
    const macro = macroCount(moves);
    const type = typeFromJeantimexBlocks(g.blocks);
    const diff =
      entry.pickMacro != null
        ? Math.abs(macro - entry.pickMacro)
        : Math.abs(macro - entry.minMoves);
    const item = { g, moves, macro, type, diff };
    if (!best || diff < best.diff) best = item;
  }
  return best;
}

function layoutFromBlocks(id, name, mode, optimal, blocks, extra) {
  validateJeantimexBlocks(blocks);
  const type = typeFromJeantimexBlocks(blocks);
  const pieces = piecesFromJeantimexBlocks(blocks);
  if (pieces[0].type !== "cao") {
    throw new Error(id + ": cao must be pieces[0] for solver");
  }
  return {
    id,
    name,
    mode,
    optimal,
    verifiedMacro: extra.verifiedMacro,
    type,
    pieces,
  };
}

const CAMPAIGN_EARLY = [
  { id: "camp-01", name: "初出茅庐", target: 3 },
  { id: "camp-02", name: "匹马单枪", target: 7 },
  { id: "camp-03", name: "兵挡将阻", target: 12 },
  { id: "camp-04", name: "众兵挡道", target: 18 },
  { id: "camp-05", name: "左右为难", target: 25 },
  { id: "camp-06", name: "齐头并进", target: 32 },
  { id: "camp-07", name: "燕飞南北", target: 38 },
  { id: "camp-08", name: "风烟四起", target: 44 },
  { id: "camp-09", name: "鸟飞汉阳", target: 50 },
  { id: "camp-10", name: "一路顺风", target: 56 },
];

const CAMPAIGN_LATE = [
  { id: "camp-11", name: "雨声淅沥", jeantimexNames: ["雨声淅沥"] },
  { id: "camp-12", name: "捷足先登", jeantimexNames: ["捷足先登"] },
  { id: "camp-13", name: "双将挡路", jeantimexNames: ["双将挡路"] },
  { id: "camp-14", name: "将拥曹营", jeantimexNames: ["将拥曹营"] },
  { id: "camp-15", name: "层层设防", jeantimexNames: ["层层设防"], pickMacro: 102 },
  { id: "camp-16", name: "指挥若定", jeantimexNames: ["指挥若定"] },
  { id: "camp-17", name: "峰回路转", jeantimexNames: ["峰回路转"] },
  { id: "camp-18", name: "横刀立马", jeantimexNames: ["横刀立马"] },
];

function buildCampaignEarly() {
  const heng = findByName("横刀立马")[0];
  const moves = solveGame(heng.blocks);
  if (!moves) throw new Error("cannot solve 横刀立马");
  let cur = cloneBlocks(heng.blocks);
  const states = [cloneBlocks(cur)];
  for (const m of moves) {
    cur = applyMove(cur, m);
    states.push(cloneBlocks(cur));
  }

  return CAMPAIGN_EARLY.map((meta) => {
    let pickIdx = 0;
    let bestDiff = Infinity;
    for (let s = 0; s < states.length; s++) {
      const rem = macroCount(moves.slice(s));
      const diff = Math.abs(rem - meta.target);
      if (diff < bestDiff) {
        bestDiff = diff;
        pickIdx = s;
      }
    }
    const verified = macroCount(moves.slice(pickIdx));
    return layoutFromBlocks(
      meta.id,
      meta.name,
      "campaign",
      verified,
      states[pickIdx],
      { verifiedMacro: verified }
    );
  });
}

function buildCampaignLate() {
  return CAMPAIGN_LATE.map((meta) => {
    const pick = pickJeantimex(meta);
    if (!pick) throw new Error("no board for " + meta.name);
    return layoutFromBlocks(
      meta.id,
      meta.name,
      "campaign",
      pick.macro,
      pick.g.blocks,
      { verifiedMacro: pick.macro }
    );
  });
}

function buildClassic() {
  const layouts = [];
  const notes = [];
  for (const entry of CLASSIC) {
    const pick = pickJeantimex(entry);
    if (!pick) throw new Error("no layout for " + entry.name);
    if (pick.macro !== entry.minMoves) {
      notes.push(
        entry.name +
          ": expected " +
          entry.minMoves +
          ", got " +
          pick.macro +
          " type " +
          pick.type
      );
    }
    if (entry.type && pick.type !== entry.type) {
      throw new Error(
        entry.name + " type mismatch " + pick.type + " != " + entry.type
      );
    }
    layouts.push(
      layoutFromBlocks(
        entry.id,
        entry.name,
        "classic",
        pick.macro,
        pick.g.blocks,
        { verifiedMacro: pick.macro }
      )
    );
  }
  return { layouts, notes };
}

function main() {
  const campaign = [...buildCampaignEarly(), ...buildCampaignLate()];
  const { layouts: classic, notes } = buildClassic();

  const out = {
    version: 2,
    board: { rows: 5, cols: 4 },
    escape: { row: ESCAPE_ROW, col: ESCAPE_COL },
    source: "jeantimex/klotski hrd-games.json (MIT) + klotski.online type codec",
    notes,
    layouts: [...campaign, ...classic],
  };

  const outPath = path.join(__dirname, "layouts.json");
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2), "utf8");
  console.log("Wrote", outPath, "layouts", out.layouts.length);
  if (notes.length) console.warn("Notes:\n" + notes.join("\n"));
}

main();
