#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成数独训练页 sudoku.html。"""

from __future__ import annotations

import argparse

import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator, tier_choice_row
from common.paths import game_page_paths

SLUG = "sudoku"

SUDOKU_TIER_SUB = {
    "intro": "四宫 · 易",
    "simple": "四宫 · 难",
    "normal": "六宫 · 易",
    "hard": "六宫 · 难",
    "master": "九宫 · 易",
    "god": "九宫 · 难",
}

EXTRA_CSS = r"""
.size-row { margin-bottom: .75rem; }

/* ── 对局区 ── */
.play-card { padding: .85rem .85rem 1rem; }
.sudoku-stage {
  display: flex;
  justify-content: center;
  padding: .65rem;
  margin: 0 0 .7rem;
  border-radius: 14px;
  background: #f0f4f2;
}
.sudoku-wrap { width: 100%; max-width: min(100%, 400px); margin: 0 auto; }
.sudoku {
  display: grid;
  width: 100%;
  aspect-ratio: 1;
  background: #1a2420;
  border: 2.5px solid #1a2420;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(26,36,33,.1);
}
.sudoku button {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0;
  margin: 0;
  padding: 0;
  line-height: 1;
  background: #fffcf8;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-variant-numeric: tabular-nums;
  font-size: clamp(.9rem, 4.2vw, 1.35rem);
  font-weight: 600;
  color: #1a5c48;
  cursor: pointer;
  transition: background .1s ease, color .1s ease;
}
.sudoku button.box-alt { background: #f0f5f2; }
.sudoku button.bdr-r-thin { border-right: 1px solid #c5d5cd; }
.sudoku button.bdr-r-thick { border-right: 2px solid #1a2420; }
.sudoku button.bdr-b-thin { border-bottom: 1px solid #c5d5cd; }
.sudoku button.bdr-b-thick { border-bottom: 2px solid #1a2420; }
.sudoku button:not(.given):hover { background: #e8f3ee; }
.sudoku button.given {
  background: #f5f8f6;
  color: #1a2420;
  font-weight: 700;
  cursor: default;
}
.sudoku button.given.box-alt { background: #e8eeeb; }
.sudoku button.related { background: #dceee6 !important; }
.sudoku button.given.related { background: #d0e4db !important; }
.sudoku button.same-num {
  color: #0a5240;
  font-weight: 700;
  background: #c8e6d8 !important;
}
.sudoku button.selected {
  background: #0f7a5a !important;
  color: #fff !important;
  font-weight: 700;
}
.sudoku button.selected.given { color: #fff !important; }
.sudoku button.conflict {
  background: #f5d4cf !important;
  color: #a33b2d !important;
}
.sudoku button.hinted { color: #9a4a12; }
.sudoku.size-4 button { font-size: clamp(1.2rem, 7vw, 1.75rem); }
.sudoku.size-6 button { font-size: clamp(1rem, 5vw, 1.35rem); }
.sudoku.size-9 button { font-size: clamp(.85rem, 3.5vw, 1.1rem); }

/* ── 操作区 ── */
.play-dock {
  padding: .65rem;
  border-radius: 14px;
  background: #f7faf8;
  border: 1px solid var(--line);
}
.numpad {
  display: flex;
  gap: .4rem;
  justify-content: center;
  flex-wrap: wrap;
}
.numpad.grid-9 {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: .4rem;
}
.numpad button {
  flex: 1 1 2.6rem;
  max-width: 3.25rem;
  height: 2.75rem;
  border: 0;
  border-radius: 10px;
  padding: 0;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #0a5240;
  background: #fff;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(26,36,33,.08);
  transition: background .1s ease, transform .08s ease;
}
.numpad.grid-9 button { max-width: none; height: 2.5rem; font-size: 1rem; }
.numpad button:hover { background: #e8f5ef; }
.numpad button:active { transform: scale(.96); }
.numpad button.clear {
  flex: 0 0 auto;
  max-width: none;
  min-width: 3.2rem;
  padding: 0 .6rem;
  font-size: .88rem;
  font-weight: 600;
  color: var(--muted);
  background: transparent;
  box-shadow: none;
  border: 1px dashed #c5d5cd;
}
.numpad button.clear:hover { background: #fff; }

.tool-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: .4rem;
  margin-top: .55rem;
  padding-top: .55rem;
  border-top: 1px solid var(--line);
}
.tool-row button {
  border: 0;
  border-radius: 10px;
  padding: .55rem .3rem;
  font: inherit;
  font-size: .84rem;
  font-weight: 600;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(26,36,33,.06);
  transition: background .1s ease;
}
.tool-row button:hover { background: #eef5f1; }
.tool-row button.tool-accent {
  color: #0a5240;
  background: #e0f0e8;
}
.play-actions { margin-top: .7rem; }
"""

BODY = r"""
  <section id="view-home">
    <h1>数<em>独</em></h1>
    <p class="sub">四宫格、六宫格、九宫格逻辑推理。支持检查、提示与撤销。</p>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-casual">
        <strong>休闲模式</strong>
        <span>自选规格，随机一题</span>
      </button>
      <button type="button" class="mode-btn" id="btn-challenge">
        <strong>挑战模式</strong>
        <span>连续 3 / 5 题，计时</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-setup" class="hidden">
    <h1>挑战</h1>
    <p class="sub">选择难度与题量。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("diff-choices", SUDOKU_TIER_SUB) + r"""
      <p style="margin:1rem 0 .5rem;color:var(--muted);font-size:.9rem">题量</p>
      <div class="choice-row two" id="count-choices">
        <button type="button" data-n="3" class="active">3 题</button>
        <button type="button" data-n="5">5 题</button>
      </div>
      <button type="button" class="primary" id="btn-start">开始挑战</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-setup-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-size" class="hidden">
    <h1>休闲</h1>
    <p class="sub">选择难度。</p>
    <div class="card size-row">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("casual-diff", SUDOKU_TIER_SUB) + r"""
      <button type="button" class="primary" id="btn-casual-start">开始</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-size-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-play" class="hidden">
    <div class="topbar">
      <span id="play-label">休闲</span>
      <span id="play-progress"></span>
      <span><strong id="timer-text">00:00</strong></span>
    </div>
    <p class="hint" id="play-hint">点格选中，再点数字填入</p>
    <div class="card play-card">
      <div class="sudoku-stage">
        <div class="sudoku-wrap"><div class="sudoku" id="board"></div></div>
      </div>
      <div class="play-dock">
        <div class="numpad" id="numpad"></div>
        <div class="tool-row">
          <button type="button" id="btn-undo">撤销</button>
          <button type="button" id="btn-check" class="tool-accent">检查</button>
          <button type="button" id="btn-hint" class="tool-accent">提示</button>
        </div>
      </div>
      <div class="actions play-actions">
        <button type="button" class="danger" id="btn-exit">退出</button>
        <button type="button" id="btn-restart">重来</button>
        <button type="button" id="btn-next">下一题</button>
      </div>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>结算</h1>
    <p class="sub" id="result-sub">本局挑战结束</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>题量</span><strong id="st-total">0</strong></li>
        <li><span>完成</span><strong id="st-done">0</strong></li>
        <li><span>总用时</span><strong id="st-time">00:00</strong></li>
        <li><span>提示</span><strong id="st-hints">0</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>
"""

SCRIPT = r"""
(function () {
  var views = {
    home: document.getElementById("view-home"),
    setup: document.getElementById("view-setup"),
    size: document.getElementById("view-size"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result")
  };

  var BOX = { 4: [2, 2], 6: [2, 3], 9: [3, 3] };

  var diffKey = "normal";
  var DIFF = {
    intro: { size: 4, givens: 10, label: "入门" },
    simple: { size: 4, givens: 8, label: "简单" },
    normal: { size: 6, givens: 24, label: "普通" },
    hard: { size: 6, givens: 20, label: "困难" },
    master: { size: 9, givens: 36, label: "大师" },
    god: { size: 9, givens: 28, label: "大神" }
  };

  function diffLabel(key) {
    var d = DIFF[key];
    return d ? d.label : key;
  }

  function applyDiff() {
    var d = DIFF[diffKey] || DIFF.normal;
    size = d.size;
  }

  var mode = "casual";
  var size = 6;
  var challengeTotal = 3;
  var puzzleIndex = 0;
  var puzzlesDone = 0;
  var totalHints = 0;
  var hintsUsed = 0;
  var startedAt = 0;
  var timerId = null;

  var solution = [];
  var givens = {};
  var board = [];
  var selected = null;
  var history = [];

  function stopTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }
  function startTimer() {
    stopTimer();
    timerId = setInterval(function () {
      document.getElementById("timer-text").textContent = fmtTime(Date.now() - startedAt);
    }, 500);
  }

  function boxOf(r, c) {
    var br = BOX[size][0], bc = BOX[size][1];
    return [Math.floor(r / br), Math.floor(c / bc)];
  }

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = (Math.random() * (i + 1)) | 0;
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  function solve(grid, n, br, bc) {
    for (var r = 0; r < n; r++) {
      for (var c = 0; c < n; c++) {
        if (grid[r][c] !== 0) continue;
        var nums = shuffle(Array.from({ length: n }, function (_, i) { return i + 1; }));
        for (var k = 0; k < nums.length; k++) {
          var v = nums[k];
          if (valid(grid, r, c, v, n, br, bc)) {
            grid[r][c] = v;
            if (solve(grid, n, br, bc)) return true;
            grid[r][c] = 0;
          }
        }
        return false;
      }
    }
    return true;
  }

  function valid(grid, r, c, v, n, br, bc) {
    for (var i = 0; i < n; i++) {
      if (grid[r][i] === v && i !== c) return false;
      if (grid[i][c] === v && i !== r) return false;
    }
    var br0 = Math.floor(r / br) * br, bc0 = Math.floor(c / bc) * bc;
    for (var i = 0; i < br; i++) {
      for (var j = 0; j < bc; j++) {
        var rr = br0 + i, cc = bc0 + j;
        if (grid[rr][cc] === v && (rr !== r || cc !== c)) return false;
      }
    }
    return true;
  }

  function countSolutions(puzzle, n, br, bc, limit) {
    var count = 0;
    function dfs() {
      if (count >= limit) return;
      for (var r = 0; r < n; r++) {
        for (var c = 0; c < n; c++) {
          if (puzzle[r][c] !== 0) continue;
          for (var v = 1; v <= n; v++) {
            if (valid(puzzle, r, c, v, n, br, bc)) {
              puzzle[r][c] = v;
              dfs();
              puzzle[r][c] = 0;
              if (count >= limit) return;
            }
          }
          return;
        }
      }
      count++;
    }
    dfs();
    return count;
  }

  function cloneGrid(grid) {
    return grid.map(function (row) { return row.slice(); });
  }

  function filledCount(grid) {
    var n = grid.length, cnt = 0;
    for (var r = 0; r < n; r++) {
      for (var c = 0; c < n; c++) {
        if (grid[r][c] !== 0) cnt++;
      }
    }
    return cnt;
  }

  function applyDigitPerm(grid, n) {
    var perm = shuffle(Array.from({ length: n }, function (_, i) { return i + 1; }));
    for (var r = 0; r < n; r++) {
      for (var c = 0; c < n; c++) {
        grid[r][c] = perm[grid[r][c] - 1];
      }
    }
  }

  function swapRows(grid, r1, r2) {
    var t = grid[r1];
    grid[r1] = grid[r2];
    grid[r2] = t;
  }

  function permuteBands(grid, n, br) {
    var numBands = n / br;
    var order = shuffle(Array.from({ length: numBands }, function (_, i) { return i; }));
    var src = cloneGrid(grid);
    for (var bi = 0; bi < numBands; bi++) {
      for (var dr = 0; dr < br; dr++) {
        grid[bi * br + dr] = src[order[bi] * br + dr].slice();
      }
    }
    for (var b = 0; b < numBands; b++) {
      var rows = shuffle(Array.from({ length: br }, function (_, i) { return b * br + i; }));
      var tmp = cloneGrid(grid);
      for (var i = 0; i < br; i++) grid[b * br + i] = tmp[rows[i]].slice();
    }
  }

  function permuteStacks(grid, n, bc) {
    var numStacks = n / bc;
    var order = shuffle(Array.from({ length: numStacks }, function (_, i) { return i; }));
    var src = cloneGrid(grid);
    for (var si = 0; si < numStacks; si++) {
      for (var dc = 0; dc < bc; dc++) {
        for (var r = 0; r < n; r++) {
          grid[r][si * bc + dc] = src[r][order[si] * bc + dc];
        }
      }
    }
    for (var s = 0; s < numStacks; s++) {
      var cols = shuffle(Array.from({ length: bc }, function (_, i) { return s * bc + i; }));
      var tmp = cloneGrid(grid);
      for (var i = 0; i < bc; i++) {
        var dst = s * bc + i;
        for (var r = 0; r < n; r++) grid[r][dst] = tmp[r][cols[i]];
      }
    }
  }

  function randomizeSolved(grid, n, br, bc) {
    applyDigitPerm(grid, n);
    permuteBands(grid, n, br);
    permuteStacks(grid, n, bc);
    if (br === bc && Math.random() < 0.5) {
      for (var r = 0; r < n; r++) {
        for (var c = r + 1; c < n; c++) {
          var t = grid[r][c];
          grid[r][c] = grid[c][r];
          grid[c][r] = t;
        }
      }
    }
  }

  function carvePuzzle(grid, n, br, bc, target) {
    var maxAttempts = n * n * 50;
    var attempts = 0;
    while (filledCount(grid) > target && attempts < maxAttempts) {
      attempts++;
      var r = randInt(n), c = randInt(n);
      if (grid[r][c] === 0) continue;
      var backup = grid[r][c];
      grid[r][c] = 0;
      var copy = cloneGrid(grid);
      if (countSolutions(copy, n, br, bc, 2) !== 1) grid[r][c] = backup;
    }
  }

  function ensureSpread(grid, sol, n, br, bc) {
    function rowCount(r) {
      var cnt = 0;
      for (var c = 0; c < n; c++) if (grid[r][c] !== 0) cnt++;
      return cnt;
    }
    function colCount(c) {
      var cnt = 0;
      for (var r = 0; r < n; r++) if (grid[r][c] !== 0) cnt++;
      return cnt;
    }
    function boxCount(bi, si) {
      var cnt = 0;
      for (var dr = 0; dr < br; dr++) {
        for (var dc = 0; dc < bc; dc++) {
          if (grid[bi * br + dr][si * bc + dc] !== 0) cnt++;
        }
      }
      return cnt;
    }
    function restoreAt(r, c) {
      if (grid[r][c] === 0) grid[r][c] = sol[r][c];
    }

    for (var r = 0; r < n; r++) {
      if (!rowCount(r)) {
        var cols = shuffle(Array.from({ length: n }, function (_, i) { return i; }));
        restoreAt(r, cols[0]);
      }
    }
    for (var c = 0; c < n; c++) {
      if (!colCount(c)) {
        var rows = shuffle(Array.from({ length: n }, function (_, i) { return i; }));
        restoreAt(rows[0], c);
      }
    }
    var numBands = n / br, numStacks = n / bc;
    for (var bi = 0; bi < numBands; bi++) {
      for (var si = 0; si < numStacks; si++) {
        if (!boxCount(bi, si)) {
          var coords = [];
          for (var dr = 0; dr < br; dr++) {
            for (var dc = 0; dc < bc; dc++) coords.push([bi * br + dr, si * bc + dc]);
          }
          coords = shuffle(coords);
          restoreAt(coords[0][0], coords[0][1]);
        }
      }
    }
  }

  function generatePuzzle(n, givensTarget) {
    var br = BOX[n][0], bc = BOX[n][1];
    var grid = [];
    for (var r = 0; r < n; r++) { grid[r] = []; for (var c = 0; c < n; c++) grid[r][c] = 0; }
    solve(grid, n, br, bc);
    randomizeSolved(grid, n, br, bc);
    var sol = cloneGrid(grid);
    var target = givensTarget || (DIFF[diffKey] || DIFF.normal).givens;
    carvePuzzle(grid, n, br, bc, target);
    ensureSpread(grid, sol, n, br, bc);
    var g = {};
    for (var r = 0; r < n; r++) {
      for (var c = 0; c < n; c++) {
        if (grid[r][c] !== 0) g[r + "," + c] = grid[r][c];
      }
    }
    return { solution: sol, givens: g, puzzle: grid };
  }

  var puzzleStart = 0;

  function loadPuzzle() {
    puzzleStart = Date.now();
    var p = generatePuzzle(size);
    solution = p.solution;
    givens = p.givens;
    board = p.puzzle.map(function (row) { return row.slice(); });
    selected = null;
    history = [];
    hintsUsed = 0;
    renderBoard();
    buildNumpad();
    document.getElementById("play-hint").className = "hint";
    document.getElementById("play-hint").textContent = "点格选中，再点数字填入";
  }

  function pushHistory() {
    history.push(board.map(function (row) { return row.slice(); }));
    if (history.length > 40) history.shift();
  }

  function isRelated(r, c, sr, sc) {
    if (r === sr && c === sc) return false;
    if (r === sr || c === sc) return true;
    var br = BOX[size][0], bc = BOX[size][1];
    var br0 = Math.floor(r / br), bc0 = Math.floor(c / bc);
    var sbr0 = Math.floor(sr / br), sbc0 = Math.floor(sc / bc);
    return br0 === sbr0 && bc0 === sbc0;
  }

  function renderBoard() {
    var el = document.getElementById("board");
    el.className = "sudoku size-" + size;
    el.style.gridTemplateColumns = "repeat(" + size + ", 1fr)";
    el.style.gridTemplateRows = "repeat(" + size + ", 1fr)";
    el.innerHTML = "";
    var br = BOX[size][0], bc = BOX[size][1];
    var sr = selected ? selected[0] : -1;
    var sc = selected ? selected[1] : -1;
    var sameVal = selected && board[sr][sc] ? board[sr][sc] : 0;
    var boxesPerRow = size / bc;
    for (var r = 0; r < size; r++) {
      for (var c = 0; c < size; c++) {
        var btn = document.createElement("button");
        btn.type = "button";
        var v = board[r][c];
        btn.textContent = v ? String(v) : "";
        var key = r + "," + c;
        var boxIdx = Math.floor(r / br) * boxesPerRow + Math.floor(c / bc);
        if (boxIdx % 2 === 1) btn.classList.add("box-alt");
        if (givens[key]) btn.classList.add("given");
        if (selected && selected[0] === r && selected[1] === c) btn.classList.add("selected");
        else if (selected && isRelated(r, c, sr, sc)) btn.classList.add("related");
        if (sameVal && v === sameVal) btn.classList.add("same-num");
        if (hasConflict(r, c, v)) btn.classList.add("conflict");
        if (c < size - 1) btn.classList.add((c + 1) % bc === 0 ? "bdr-r-thick" : "bdr-r-thin");
        if (r < size - 1) btn.classList.add((r + 1) % br === 0 ? "bdr-b-thick" : "bdr-b-thin");
        btn.dataset.r = String(r);
        btn.dataset.c = String(c);
        if (!givens[key]) btn.addEventListener("click", function () {
          selected = [Number(this.dataset.r), Number(this.dataset.c)];
          renderBoard();
        });
        el.appendChild(btn);
      }
    }
  }

  function hasConflict(r, c, v) {
    if (!v) return false;
    for (var i = 0; i < size; i++) {
      if (i !== c && board[r][i] === v) return true;
      if (i !== r && board[i][c] === v) return true;
    }
    var br = BOX[size][0], bc = BOX[size][1];
    var br0 = Math.floor(r / br) * br, bc0 = Math.floor(c / bc) * bc;
    for (var i = 0; i < br; i++) {
      for (var j = 0; j < bc; j++) {
        var rr = br0 + i, cc = bc0 + j;
        if ((rr !== r || cc !== c) && board[rr][cc] === v) return true;
      }
    }
    return false;
  }

  function buildNumpad() {
    var pad = document.getElementById("numpad");
    pad.innerHTML = "";
    pad.className = "numpad" + (size > 6 ? " grid-9" : "");
    for (var i = 1; i <= size; i++) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = String(i);
      b.addEventListener("click", (function (n) {
        return function () { setCell(n); };
      })(i));
      pad.appendChild(b);
    }
    var clr = document.createElement("button");
    clr.type = "button";
    clr.className = "clear";
    clr.textContent = "清除";
    clr.addEventListener("click", function () { setCell(0); });
    pad.appendChild(clr);
  }

  function setCell(n) {
    if (!selected) return;
    var r = selected[0], c = selected[1];
    if (givens[r + "," + c]) return;
    if (board[r][c] === n) return;
    pushHistory();
    board[r][c] = n;
    renderBoard();
    if (isComplete()) onPuzzleDone();
  }

  function isComplete() {
    for (var r = 0; r < size; r++) {
      for (var c = 0; c < size; c++) {
        if (!board[r][c] || hasConflict(r, c, board[r][c])) return false;
      }
    }
    return true;
  }

  function onPuzzleDone() {
    document.getElementById("play-hint").className = "hint ok";
    document.getElementById("play-hint").textContent = "完成！";
    if (mode === "challenge") {
      puzzlesDone++;
      totalHints += hintsUsed;
      puzzleIndex++;
      if (puzzleIndex >= challengeTotal) {
        celebrateThen(FGB_MSG.sessionDone, finishChallenge, 500);
      } else {
        document.getElementById("play-progress").textContent =
          (puzzleIndex + 1) + " / " + challengeTotal;
        celebrateThen(FGB_MSG.done, loadPuzzle, 480);
      }
    } else {
      celebrate(FGB_MSG.done);
      if (typeof fgbSubmitScore === "function") fgbSubmitScore({
        gameId: "sudoku", mode: "casual", tier: diffKey,
        metrics: { timeMs: Date.now() - puzzleStart, hints: hintsUsed }
      });
    }
  }

  function startCasualPlay() {
    mode = "casual";
    applyDiff();
    stopTimer();
    document.getElementById("play-label").textContent = "休闲 · " + diffLabel(diffKey);
    document.getElementById("play-progress").textContent = "";
    document.getElementById("timer-text").textContent = "—";
    document.getElementById("btn-next").style.display = "";
    showView(views, "play");
    loadPuzzle();
  }

  function startChallenge() {
    mode = "challenge";
    applyDiff();
    puzzleIndex = 0;
    puzzlesDone = 0;
    totalHints = 0;
    startedAt = Date.now();
    document.getElementById("play-label").textContent = "挑战 · " + diffLabel(diffKey);
    document.getElementById("btn-next").style.display = "none";
    showView(views, "play");
    startTimer();
    document.getElementById("play-progress").textContent = "1 / " + challengeTotal;
    loadPuzzle();
  }

  function finishChallenge() {
    stopTimer();
    document.getElementById("st-total").textContent = String(challengeTotal);
    document.getElementById("st-done").textContent = String(puzzlesDone);
    document.getElementById("st-time").textContent = fmtTime(Date.now() - startedAt);
    document.getElementById("st-hints").textContent = String(totalHints);
    showView(views, "result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") fgbSubmitScore({
      gameId: "sudoku", mode: "challenge", tier: diffKey,
      metrics: {
        done: puzzlesDone, total: challengeTotal,
        timeMs: Date.now() - startedAt, hints: totalHints
      }
    });
  }

  function bindDiffChoice(selector) {
    document.querySelectorAll(selector).forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(selector).forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        diffKey = btn.dataset.diff;
        applyDiff();
      });
    });
  }

  document.getElementById("btn-casual").addEventListener("click", function () { showView(views, "size"); });
  document.getElementById("btn-challenge").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-setup-back").addEventListener("click", function () { showView(views, "home"); });
  document.getElementById("btn-size-back").addEventListener("click", function () { showView(views, "home"); });
  bindDiffChoice("#diff-choices button");
  bindDiffChoice("#casual-diff button");
  document.querySelectorAll("#count-choices button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#count-choices button").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      challengeTotal = Number(btn.dataset.n);
    });
  });
  document.getElementById("btn-casual-start").addEventListener("click", startCasualPlay);
  document.getElementById("btn-start").addEventListener("click", startChallenge);
  document.getElementById("btn-undo").addEventListener("click", function () {
    if (!history.length) return;
    board = history.pop();
    renderBoard();
  });
  document.getElementById("btn-check").addEventListener("click", function () {
    var bad = false;
    for (var r = 0; r < size; r++) {
      for (var c = 0; c < size; c++) {
        if (board[r][c] && hasConflict(r, c, board[r][c])) bad = true;
      }
    }
    document.getElementById("play-hint").className = "hint " + (bad ? "err" : "ok");
    document.getElementById("play-hint").textContent = bad ? "存在冲突" : "目前没有冲突";
    renderBoard();
  });
  document.getElementById("btn-hint").addEventListener("click", function () {
    if (!selected || givens[selected[0] + "," + selected[1]]) {
      document.getElementById("play-hint").textContent = "请先选中一个空格";
      return;
    }
    pushHistory();
    board[selected[0]][selected[1]] = solution[selected[0]][selected[1]];
    hintsUsed++;
    renderBoard();
    if (isComplete()) onPuzzleDone();
  });
  document.getElementById("btn-exit").addEventListener("click", function () {
    function doExit() {
      stopTimer();
      if (mode === "challenge" && puzzleIndex > 0) finishChallenge();
      else showView(views, "home");
    }
    if (mode === "challenge" && puzzleIndex > 0) {
      askConfirm(FGB_MSG.exitConfirm, doExit);
      return;
    }
    doExit();
  });
  document.getElementById("btn-restart").addEventListener("click", loadPuzzle);
  document.getElementById("btn-next").addEventListener("click", loadPuzzle);
  document.getElementById("btn-again").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-home").addEventListener("click", function () { stopTimer(); showView(views, "home"); });

  if (window.__FGB_IS_DAILY__) {
    var dq = window.__FGB_DAILY_Q__ || {};
    if (dq.tier && DIFF[dq.tier]) { diffKey = dq.tier; applyDiff(); }
    startCasualPlay();
  } else {
    showView(views, "home");
  }
})();
"""


def build_html() -> str:
    return build_page("数独", EXTRA_CSS, inject_lobby_link(BODY), SCRIPT, wide=True)


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate sudoku training HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
