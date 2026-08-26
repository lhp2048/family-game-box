#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成迷宫训练页 maze.html。"""

from __future__ import annotations

import argparse

import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator, tier_choice_row
from common.paths import game_page_paths

SLUG = "maze"

MAZE_TIER_SUB = {
    "intro": "9×9",
    "simple": "11×11",
    "normal": "15×15",
    "hard": "19×19",
    "master": "21×21",
    "god": "31×31",
}

EXTRA_CSS = r"""
.maze-wrap {
  display: flex;
  justify-content: center;
  margin: .5rem 0;
  overflow: auto;
  max-height: min(70vh, 720px);
}
.maze {
  display: grid;
  gap: 0;
  border: 2px solid var(--ink);
  background: var(--ink);
}
.maze .cell {
  width: 18px;
  height: 18px;
  border-radius: 0;
  aspect-ratio: auto;
  min-height: 0;
  cursor: default;
  flex-shrink: 0;
}
.maze .wall { background: #2a3530; }
.maze .path { background: #fffdf8; cursor: pointer; }
.maze .path:hover { background: #eef6f1; }
.maze .start { background: #9fd6bf; }
.maze .end { background: #e8b88a; }
.maze .player {
  background: var(--accent);
  box-shadow: inset 0 0 0 2px #fff;
}
/* 走过痕迹：浅琥珀，与深色墙明显区分 */
.maze .path.in-trail { background: #f3e6c4; }
.maze .path.in-trail:hover { background: #ead9a8; }
.maze .start.in-trail { background: #8fcbb0; }
.maze .end.in-trail { background: #dfa978; }
.stat-pills {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: .9rem;
  color: var(--muted);
  margin-bottom: .5rem;
}
.stat-pills strong { color: var(--ink); }
.choice-row button span {
  display: block;
  font-weight: 500;
  font-size: .78rem;
  margin-top: .15rem;
  opacity: .85;
}
"""

BODY = r"""
  <section id="view-home">
    <h1>迷宫<em>追踪</em></h1>
    <p class="sub">从起点走到终点。同一方向无墙阻挡时，可一次走到该方向上的任意格。难度由迷宫整体规模控制，单格大小固定。</p>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-casual">
        <strong>休闲模式</strong>
        <span>自选规模，到达终点即可</span>
      </button>
      <button type="button" class="mode-btn" id="btn-challenge">
        <strong>挑战模式</strong>
        <span>固定规模连做，计时统计</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-casual" class="hidden">
    <h1>休闲</h1>
    <p class="sub">选择难度（迷宫规模，单格固定 18px）。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("casual-diff", MAZE_TIER_SUB) + r"""
      <button type="button" class="primary" id="btn-casual-start">开始</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-casual-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-setup" class="hidden">
    <h1>挑战</h1>
    <p class="sub">选择规模与关数。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("diff-choices", MAZE_TIER_SUB) + r"""
      <p style="margin:1rem 0 .5rem;color:var(--muted);font-size:.9rem">关数</p>
      <div class="choice-row two" id="count-choices">
        <button type="button" data-n="3" class="active">3 关</button>
        <button type="button" data-n="5">5 关</button>
      </div>
      <button type="button" class="primary" id="btn-start">开始挑战</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-setup-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-play" class="hidden">
    <div class="topbar">
      <span id="play-label">休闲</span>
      <span id="play-progress"></span>
      <span><strong id="timer-text">00:00</strong></span>
    </div>
    <div class="stat-pills">
      <span>步数 <strong id="steps">0</strong></span>
      <span>碰墙 <strong id="bumps">0</strong></span>
      <span>最短 <strong id="shortest">—</strong></span>
    </div>
    <p class="hint" id="play-hint">点击同行或同列、路径畅通的格子移动</p>
    <div class="card">
      <div class="maze-wrap"><div class="maze" id="maze"></div></div>
      <div class="actions">
        <button type="button" class="danger" id="btn-exit">退出</button>
        <button type="button" id="btn-restart">重来</button>
        <button type="button" id="btn-new">新迷宫</button>
      </div>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>结算</h1>
    <p class="sub" id="result-sub">本局挑战结束</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>关卡</span><strong id="st-rounds">0</strong></li>
        <li><span>规模</span><strong id="st-size">9×9</strong></li>
        <li><span>完成</span><strong id="st-done">0</strong></li>
        <li><span>总用时</span><strong id="st-time">00:00</strong></li>
        <li><span>总步数</span><strong id="st-steps">0</strong></li>
        <li><span>效率均值</span><strong id="st-eff">—</strong></li>
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
    casual: document.getElementById("view-casual"),
    setup: document.getElementById("view-setup"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result")
  };

  var diffKey = "normal";
  var mazeSize = 15;
  var mode = "casual";
  var challengeTotal = 3;
  var levelIndex = 0;
  var levelsDone = 0;
  var totalSteps = 0;
  var effSum = 0;
  var startedAt = 0;
  var timerId = null;

  var maze = null;
  var player = null;
  var steps = 0;
  var bumps = 0;
  var trail = {};

  function stopTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }
  function startTimer() {
    stopTimer();
    timerId = setInterval(function () {
      document.getElementById("timer-text").textContent = fmtTime(Date.now() - startedAt);
    }, 500);
  }

  var DIFF = {
    intro: { size: 9, label: "入门" },
    simple: { size: 11, label: "简单" },
    normal: { size: 15, label: "普通" },
    hard: { size: 19, label: "困难" },
    master: { size: 21, label: "大师" },
    god: { size: 31, label: "大神" }
  };

  function diffLabel(key) {
    var d = DIFF[key];
    return d ? d.label : key;
  }

  function applyDiff() {
    var d = DIFF[diffKey] || DIFF.normal;
    mazeSize = d.size;
  }

  function modeLabel() {
    return (mode === "casual" ? "休闲" : "挑战") + " · " + diffLabel(diffKey);
  }

  function makeOdd(n) { return n % 2 === 0 ? n + 1 : n; }

  function generateMaze(size) {
    size = makeOdd(size);
    var grid = [];
    var r, c, i;
    for (r = 0; r < size; r++) {
      grid[r] = [];
      for (c = 0; c < size; c++) grid[r][c] = 1;
    }

    var dirs = [[0, 2], [0, -2], [2, 0], [-2, 0]];
    var startR = 1, startC = 1;
    grid[startR][startC] = 0;
    var active = [[startR, startC]];

    while (active.length) {
      var idx = Math.random() < 0.65 ? active.length - 1 : randInt(active.length);
      var cur = active[idx];
      var cr = cur[0], cc = cur[1];
      var neighbors = [];
      for (i = 0; i < dirs.length; i++) {
        var nr = cr + dirs[i][0], nc = cc + dirs[i][1];
        if (nr > 0 && nr < size - 1 && nc > 0 && nc < size - 1 && grid[nr][nc] === 1) {
          neighbors.push([nr, nc, dirs[i][0], dirs[i][1]]);
        }
      }
      if (!neighbors.length) {
        active.splice(idx, 1);
        continue;
      }
      var pickN = neighbors[randInt(neighbors.length)];
      var wr = cr + pickN[2] / 2, wc = cc + pickN[3] / 2;
      grid[wr][wc] = 0;
      grid[pickN[0]][pickN[1]] = 0;
      active.push([pickN[0], pickN[1]]);
    }

    braidMaze(grid, size, size < 15 ? 0.02 : size < 25 ? 0.035 : 0.05);

    var start = [startR, startC];
    var end = farthestCell(grid, size, start);
    return { size: size, grid: grid, start: start, end: end };
  }

  function braidMaze(grid, size, rate) {
    var candidates = [];
    var r, c;
    for (r = 1; r < size - 1; r++) {
      for (c = 1; c < size - 1; c++) {
        if (grid[r][c] !== 1) continue;
        var horiz = grid[r][c - 1] === 0 && grid[r][c + 1] === 0 && grid[r - 1][c] === 1 && grid[r + 1][c] === 1;
        var vert = grid[r - 1][c] === 0 && grid[r + 1][c] === 0 && grid[r][c - 1] === 1 && grid[r][c + 1] === 1;
        if (horiz || vert) candidates.push([r, c]);
      }
    }
    candidates = shuffle(candidates);
    var n = Math.max(0, Math.floor(candidates.length * rate));
    for (var i = 0; i < n; i++) {
      grid[candidates[i][0]][candidates[i][1]] = 0;
    }
  }

  function farthestCell(grid, size, start) {
    var q = [[start[0], start[1], 0]];
    var qi = 0;
    var seen = {};
    seen[start[0] + "," + start[1]] = true;
    var best = [start[0], start[1]];
    var bestD = 0;
    var dirs = [[0, 1], [0, -1], [1, 0], [-1, 0]];
    while (qi < q.length) {
      var cur = q[qi++];
      if (cur[2] > bestD) {
        bestD = cur[2];
        best = [cur[0], cur[1]];
      }
      for (var i = 0; i < dirs.length; i++) {
        var nr = cur[0] + dirs[i][0], nc = cur[1] + dirs[i][1];
        if (nr < 0 || nr >= size || nc < 0 || nc >= size || grid[nr][nc] !== 0) continue;
        var key = nr + "," + nc;
        if (seen[key]) continue;
        seen[key] = true;
        q.push([nr, nc, cur[2] + 1]);
      }
    }
    return best;
  }

  function bfsShortest(m) {
    var q = [[m.start[0], m.start[1], 0]];
    var qi = 0;
    var seen = {};
    seen[m.start[0] + "," + m.start[1]] = true;
    var dirs = [[0, 1], [0, -1], [1, 0], [-1, 0]];
    while (qi < q.length) {
      var cur = q[qi++];
      if (cur[0] === m.end[0] && cur[1] === m.end[1]) return cur[2];
      for (var i = 0; i < dirs.length; i++) {
        var nr = cur[0] + dirs[i][0], nc = cur[1] + dirs[i][1];
        if (nr < 0 || nr >= m.size || nc < 0 || nc >= m.size || m.grid[nr][nc] !== 0) continue;
        var key = nr + "," + nc;
        if (seen[key]) continue;
        seen[key] = true;
        q.push([nr, nc, cur[2] + 1]);
      }
    }
    return 0;
  }

  var levelStart = 0;

  function loadLevel(size) {
    levelStart = Date.now();
    maze = generateMaze(size);
    maze.shortest = bfsShortest(maze);
    player = maze.start.slice();
    steps = 0;
    bumps = 0;
    trail = {};
    trail[player[0] + "," + player[1]] = true;
    document.getElementById("steps").textContent = "0";
    document.getElementById("bumps").textContent = "0";
    document.getElementById("shortest").textContent = String(maze.shortest);
    renderMaze();
  }

  function renderMaze() {
    var el = document.getElementById("maze");
    el.style.gridTemplateColumns = "repeat(" + maze.size + ", 18px)";
    el.innerHTML = "";
    for (var r = 0; r < maze.size; r++) {
      for (var c = 0; c < maze.size; c++) {
        var cell = document.createElement("div");
        cell.className = "cell";
        if (maze.grid[r][c] === 1) cell.classList.add("wall");
        else {
          cell.classList.add("path");
          if (r === maze.start[0] && c === maze.start[1]) cell.classList.add("start");
          if (r === maze.end[0] && c === maze.end[1]) cell.classList.add("end");
          if (trail[r + "," + c]) cell.classList.add("in-trail");
          if (r === player[0] && c === player[1]) cell.classList.add("player");
          cell.dataset.r = String(r);
          cell.dataset.c = String(c);
          cell.addEventListener("click", onCellClick);
        }
        el.appendChild(cell);
      }
    }
  }

  function canSlideTo(r, c) {
    var pr = player[0], pc = player[1];
    if (r === pr && c === pc) return null;
    if (r !== pr && c !== pc) return null;
    if (maze.grid[r][c] === 1) return null;
    var dr = r === pr ? 0 : (r > pr ? 1 : -1);
    var dc = c === pc ? 0 : (c > pc ? 1 : -1);
    var path = [];
    var cr = pr + dr, cc = pc + dc;
    while (true) {
      if (maze.grid[cr][cc] === 1) return null;
      path.push([cr, cc]);
      if (cr === r && cc === c) return path;
      cr += dr;
      cc += dc;
    }
  }

  function onCellClick() {
    var r = Number(this.dataset.r), c = Number(this.dataset.c);
    if (r === player[0] && c === player[1]) return;
    if (maze.grid[r][c] === 1) {
      bumps++;
      document.getElementById("bumps").textContent = String(bumps);
      document.getElementById("play-hint").className = "hint err";
      document.getElementById("play-hint").textContent = "撞墙了";
      return;
    }
    var path = canSlideTo(r, c);
    if (!path) {
      document.getElementById("play-hint").className = "hint err";
      document.getElementById("play-hint").textContent = "只能沿同一方向、无墙阻挡移动";
      return;
    }
    for (var i = 0; i < path.length; i++) {
      trail[path[i][0] + "," + path[i][1]] = true;
    }
    player = [r, c];
    steps += path.length;
    document.getElementById("steps").textContent = String(steps);
    document.getElementById("play-hint").className = "hint";
    document.getElementById("play-hint").textContent = "点击同行或同列、路径畅通的格子移动";
    renderMaze();
    if (r === maze.end[0] && c === maze.end[1]) onComplete();
  }

  function onComplete() {
    document.getElementById("play-hint").className = "hint ok";
    document.getElementById("play-hint").textContent = "到达终点！";
    if (mode === "challenge") {
      levelsDone++;
      totalSteps += steps;
      effSum += steps / maze.shortest;
      levelIndex++;
      if (levelIndex >= challengeTotal) {
        celebrateThen(FGB_MSG.sessionDone, finishChallenge, 500);
      } else {
        document.getElementById("play-progress").textContent = (levelIndex + 1) + " / " + challengeTotal;
        celebrateThen(FGB_MSG.done, function () { loadLevel(mazeSize); }, 480);
      }
    } else {
      celebrate(FGB_MSG.done);
      if (typeof fgbSubmitScore === "function") fgbSubmitScore({
        gameId: "maze", mode: "casual", tier: diffKey,
        metrics: { timeMs: Date.now() - levelStart, steps: steps }
      });
    }
  }

  function startCasual() {
    mode = "casual";
    applyDiff();
    stopTimer();
    document.getElementById("play-label").textContent = modeLabel();
    document.getElementById("play-progress").textContent = "";
    document.getElementById("timer-text").textContent = "—";
    showView(views, "play");
    loadLevel(mazeSize);
  }

  function startChallenge() {
    mode = "challenge";
    applyDiff();
    levelIndex = 0;
    levelsDone = 0;
    totalSteps = 0;
    effSum = 0;
    startedAt = Date.now();
    document.getElementById("play-label").textContent = modeLabel();
    showView(views, "play");
    startTimer();
    document.getElementById("play-progress").textContent = "1 / " + challengeTotal;
    loadLevel(mazeSize);
  }

  function finishChallenge() {
    stopTimer();
    document.getElementById("st-rounds").textContent = String(challengeTotal);
    document.getElementById("st-size").textContent = mazeSize + "×" + mazeSize;
    document.getElementById("st-done").textContent = String(levelsDone);
    document.getElementById("st-time").textContent = fmtTime(Date.now() - startedAt);
    document.getElementById("st-steps").textContent = String(totalSteps);
    document.getElementById("st-eff").textContent = levelsDone
      ? (effSum / levelsDone).toFixed(2) : "—";
    showView(views, "result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") fgbSubmitScore({
      gameId: "maze", mode: "challenge", tier: diffKey,
      metrics: {
        done: levelsDone, total: challengeTotal,
        timeMs: Date.now() - startedAt, steps: totalSteps
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

  document.getElementById("btn-casual").addEventListener("click", function () { showView(views, "casual"); });
  document.getElementById("btn-challenge").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-casual-back").addEventListener("click", function () { showView(views, "home"); });
  document.getElementById("btn-setup-back").addEventListener("click", function () { showView(views, "home"); });
  bindDiffChoice("#casual-diff button");
  bindDiffChoice("#diff-choices button");
  document.querySelectorAll("#count-choices button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#count-choices button").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      challengeTotal = Number(btn.dataset.n);
    });
  });
  document.getElementById("btn-casual-start").addEventListener("click", startCasual);
  document.getElementById("btn-start").addEventListener("click", startChallenge);
  document.getElementById("btn-exit").addEventListener("click", function () {
    function doExit() {
      stopTimer();
      if (mode === "challenge" && levelIndex > 0) finishChallenge();
      else showView(views, "home");
    }
    if (mode === "challenge" && levelIndex > 0) {
      askConfirm(FGB_MSG.exitConfirm, doExit);
      return;
    }
    doExit();
  });
  document.getElementById("btn-restart").addEventListener("click", function () {
    player = maze.start.slice();
    steps = 0;
    trail = {};
    trail[player[0] + "," + player[1]] = true;
    document.getElementById("steps").textContent = "0";
    renderMaze();
  });
  document.getElementById("btn-new").addEventListener("click", function () {
    loadLevel(mazeSize);
  });
  document.getElementById("btn-again").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-home").addEventListener("click", function () { stopTimer(); showView(views, "home"); });

  showView(views, "home");
})();
"""


def build_html() -> str:
    return build_page("迷宫追踪", EXTRA_CSS, inject_lobby_link(BODY), SCRIPT, wide=True)


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate maze training HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
