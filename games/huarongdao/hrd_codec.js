#!/usr/bin/env node
/* eslint-disable no-console */
"use strict";

/**
 * klotski.online 布局编码：0 空 · 1 卒 · 2 竖将 · 3 横将 · 4 曹操
 * 20 位字符串，4 列 × 5 行，行优先。
 */

const ROWS = 5;
const COLS = 4;
const V_LABELS = ["张", "赵", "马", "黄"];

function gridFromType(type) {
  const s = String(type || "").trim();
  if (s.length !== ROWS * COLS) {
    throw new Error("type length must be 20, got " + s.length);
  }
  const grid = [];
  for (let r = 0; r < ROWS; r++) {
    grid[r] = [];
    for (let c = 0; c < COLS; c++) {
      grid[r][c] = parseInt(s[r * COLS + c], 10);
    }
  }
  return grid;
}

function typeFromGrid(grid) {
  let out = "";
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      out += String(grid[r][c]);
    }
  }
  return out;
}

function countEmpties(grid) {
  let n = 0;
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      if (grid[r][c] === 0) n++;
    }
  }
  return n;
}

function blocksFromGrid(grid) {
  const seen = Array.from({ length: ROWS }, () => Array(COLS).fill(false));
  const blocks = [];

  function mark(r, c, h, w) {
    for (let dr = 0; dr < h; dr++) {
      for (let dc = 0; dc < w; dc++) {
        seen[r + dr][c + dc] = true;
      }
    }
  }

  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      if (seen[r][c]) continue;
      const d = grid[r][c];
      if (d === 0) {
        seen[r][c] = true;
        continue;
      }
      let h = 1;
      let w = 1;
      if (d === 4) {
        h = 2;
        w = 2;
      } else if (d === 2) {
        h = 2;
        w = 1;
      } else if (d === 3) {
        h = 1;
        w = 2;
      } else if (d === 1) {
        h = 1;
        w = 1;
      } else {
        throw new Error("invalid digit " + d + " at " + r + "," + c);
      }
      for (let dr = 0; dr < h; dr++) {
        for (let dc = 0; dc < w; dc++) {
          if (grid[r + dr][c + dc] !== d) {
            throw new Error("inconsistent block at " + r + "," + c);
          }
        }
      }
      mark(r, c, h, w);
      blocks.push({ shape: [h, w], position: [r, c], digit: d });
    }
  }
  return blocks;
}

function blocksFromType(type) {
  return blocksFromGrid(gridFromType(type));
}

function gridFromJeantimexBlocks(blocks) {
  const grid = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
  for (const b of blocks) {
    const h = b.shape[0];
    const w = b.shape[1];
    const [r, c] = b.position;
    let d = 1;
    if (w === 2 && h === 2) d = 4;
    else if (w === 1 && h === 2) d = 2;
    else if (w === 2 && h === 1) d = 3;
    else if (w === 1 && h === 1) d = 1;
    for (let dr = 0; dr < h; dr++) {
      for (let dc = 0; dc < w; dc++) {
        grid[r + dr][c + dc] = d;
      }
    }
  }
  return grid;
}

function typeFromJeantimexBlocks(blocks) {
  return typeFromGrid(gridFromJeantimexBlocks(blocks));
}

function taggedBlocksFromJeantimex(blocks) {
  const grid = gridFromJeantimexBlocks(blocks);
  return blocks.map((b) => {
    const [r, c] = b.position;
    return {
      shape: b.shape.slice(),
      position: b.position.slice(),
      digit: grid[r][c],
    };
  });
}

function piecesFromJeantimexBlocks(blocks) {
  const tagged = taggedBlocksFromJeantimex(blocks);
  const caoIdx = tagged.findIndex((b) => b.digit === 4);
  if (caoIdx < 0) throw new Error("missing cao block");

  const vertical = tagged
    .filter((b) => b.digit === 2)
    .sort((a, b) => a.position[0] - b.position[0] || a.position[1] - b.position[1]);
  const horizontals = tagged
    .filter((b) => b.digit === 3)
    .sort((a, b) => a.position[0] - b.position[0] || a.position[1] - b.position[1]);
  const soldiers = tagged
    .filter((b) => b.digit === 1)
    .sort((a, b) => a.position[0] - b.position[0] || a.position[1] - b.position[1]);

  const pieces = [];

  function pushPiece(b, type, label, id) {
    pieces.push({
      id,
      type,
      label,
      r: b.position[0],
      c: b.position[1],
      w: b.shape[1],
      h: b.shape[0],
    });
  }

  pushPiece(tagged[caoIdx], "cao", "曹", "cao");
  vertical.forEach((b, i) => {
    pushPiece(b, "v", V_LABELS[i % V_LABELS.length], "v" + i);
  });
  horizontals.forEach((b, i) => {
    if (i === 0) pushPiece(b, "guan", "关", "guan");
    else pushPiece(b, "h", "横", "h" + i);
  });
  soldiers.forEach((b, i) => {
    pushPiece(b, "s", "兵", "s" + i);
  });

  return pieces;
}

function validateJeantimexBlocks(blocks) {
  const grid = gridFromJeantimexBlocks(blocks);
  const empties = countEmpties(grid);
  if (empties !== 2) {
    throw new Error("expected 2 empties, got " + empties);
  }
  blocksFromGrid(grid);
  const type = typeFromGrid(grid);
  return { grid, type, empties };
}

function jeantimexBlocksFromTaggedPieces(pieces) {
  return pieces.map((p) => ({
    shape: [p.h, p.w],
    position: [p.r, p.c],
  }));
}

module.exports = {
  ROWS,
  COLS,
  V_LABELS,
  gridFromType,
  typeFromGrid,
  blocksFromType,
  blocksFromGrid,
  gridFromJeantimexBlocks,
  typeFromJeantimexBlocks,
  taggedBlocksFromJeantimex,
  piecesFromJeantimexBlocks,
  validateJeantimexBlocks,
  countEmpties,
  jeantimexBlocksFromTaggedPieces,
};
