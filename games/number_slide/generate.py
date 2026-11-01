#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「数字华容道」滑动拼图页。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator
from common.paths import game_page_paths

SLUG = "number-slide"

EXTRA_CSS = r"""
.ns-hero { text-align: center; margin-bottom: 1rem; }
.ns-tag {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.35rem;
}
.ns-tier-grid {
  display: grid;
  gap: 0.65rem;
  margin-bottom: 0.85rem;
}
.ns-tier-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  font: inherit;
  cursor: pointer;
  box-shadow: 0 4px 0 rgba(26, 43, 60, 0.05);
  transition: border-color 0.15s ease, transform 0.15s ease;
}
.ns-tier-btn strong { font-family: var(--display); font-size: 1.05rem; }
.ns-tier-btn span { font-size: 0.82rem; color: var(--muted); margin-top: 0.2rem; line-height: 1.4; }
.ns-tier-btn:hover, .ns-tier-btn:focus-visible {
  border-color: rgba(96, 165, 250, 0.55);
  outline: none;
  transform: translateY(-1px);
}
.ns-tier-btn.active {
  border-color: rgba(96, 165, 250, 0.65);
  background: rgba(96, 165, 250, 0.12);
}
.ns-hud {
  display: flex;
  justify-content: center;
  gap: 1.25rem;
  flex-wrap: wrap;
  margin-bottom: 0.65rem;
  font-size: 0.92rem;
  color: var(--muted);
}
.ns-hud strong {
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  font-family: var(--display);
  font-size: 1.1rem;
}
.ns-board-wrap {
  display: flex;
  justify-content: center;
  margin: 0.35rem 0 0.75rem;
  touch-action: manipulation;
}
.ns-board {
  display: grid;
  gap: clamp(2px, 0.45vw, 5px);
  width: min(100%, min(78vmin, 440px));
  aspect-ratio: 1;
  padding: clamp(4px, 1vw, 8px);
  border-radius: 18px;
  border: 2px solid rgba(96, 165, 250, 0.35);
  background: linear-gradient(165deg, #eef4ff 0%, #e8f8f0 55%, #fff5e8 100%);
  box-shadow: 0 10px 28px rgba(45, 62, 90, 0.1);
}
.ns-board button {
  margin: 0;
  padding: 0;
  border: 2px solid rgba(26, 43, 60, 0.08);
  border-radius: clamp(8px, 1.2vw, 14px);
  background: linear-gradient(180deg, #fff 0%, #f0f7ff 100%);
  box-shadow: 0 3px 0 rgba(26, 43, 60, 0.06);
  color: #1a2b3c;
  font-family: var(--display);
  font-weight: 700;
  font-size: clamp(0.85rem, 4.2vw, 1.45rem);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  min-height: 0;
  aspect-ratio: 1;
  transition: transform 0.1s ease, background 0.12s ease, border-color 0.12s ease;
}
.ns-board button:hover:not(:disabled) {
  border-color: rgba(96, 165, 250, 0.45);
  background: rgba(96, 165, 250, 0.18);
}
.ns-board button:active:not(:disabled) { transform: scale(0.96); }
.ns-board button.is-blank {
  visibility: hidden;
  pointer-events: none;
}
.ns-board button.is-near {
  box-shadow: inset 0 0 0 2px rgba(96, 165, 250, 0.35);
}
.ns-board button.is-settled {
  border-color: rgba(62, 207, 142, 0.5);
  background: linear-gradient(
    165deg,
    rgba(62, 207, 142, 0.24),
    rgba(62, 207, 142, 0.08)
  );
  color: #0d4d32;
  box-shadow: inset 0 0 0 2px rgba(62, 207, 142, 0.45);
}
.ns-board button.is-settled:hover:not(:disabled) {
  border-color: rgba(62, 207, 142, 0.65);
  background: linear-gradient(
    165deg,
    rgba(62, 207, 142, 0.32),
    rgba(62, 207, 142, 0.12)
  );
}
.ns-board button.is-settled.is-near {
  box-shadow:
    inset 0 0 0 2px rgba(96, 165, 250, 0.35),
    inset 0 0 0 1px rgba(62, 207, 142, 0.45);
}
html.fgb-daily-mode .ns-board {
  width: min(100%, var(--fgb-board, 360px));
  max-width: min(100%, var(--fgb-board, 360px));
}
@media (orientation: landscape) and (max-height: 520px) {
  .ns-board { width: min(48vmin, 360px); }
}
"""

BODY = r"""
  <section id="view-home">
    <div class="ns-hero">
      <p class="ns-tag">滑动拼图</p>
      <h1>数字<em>华容道</em></h1>
      <p class="sub">把 1…n²−1 按顺序排好，空格在右下角。点邻格或方向键移动。</p>
    </div>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">选择规模</p>
      <div class="ns-tier-grid" id="tier-pick">
        <button type="button" class="ns-tier-btn active" data-tier="intro">
          <strong>4×4 入门</strong>
          <span>约 40～80 步洗牌 · 适合热身</span>
        </button>
        <button type="button" class="ns-tier-btn" data-tier="normal">
          <strong>5×5 进阶</strong>
          <span>约 80～140 步洗牌</span>
        </button>
        <button type="button" class="ns-tier-btn" data-tier="hard">
          <strong>6×6 挑战</strong>
          <span>约 120～220 步洗牌</span>
        </button>
      </div>
      <button type="button" class="primary" id="btn-start">开始</button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-play" class="hidden">
    <div class="topbar">
      <span id="play-label">4×4 入门</span>
      <span id="play-hint-label">目标：升序 · 空格右下</span>
    </div>
    <div class="ns-hud">
      <span>步数 <strong id="ns-moves">0</strong></span>
      <span>用时 <strong id="ns-timer">00:00</strong></span>
    </div>
    <div class="card">
      <div class="ns-board-wrap" data-fgb-board>
        <div class="ns-board" id="ns-board" role="grid" aria-label="数字华容道棋盘"></div>
      </div>
      <p class="hint" id="play-hint">点击与空格相邻的数字，或用方向键移动</p>
      <div class="actions two">
        <button type="button" class="danger" id="btn-exit">退出</button>
        <button type="button" id="btn-restart">重开本局</button>
      </div>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>完成！</h1>
    <p class="sub" id="result-sub">拼图已还原</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>规模</span><strong id="st-size">4×4</strong></li>
        <li><span>步数</span><strong id="st-moves">0</strong></li>
        <li><span>用时</span><strong id="st-time">00:00</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>
"""

SCRIPT = r"""
(function () {
  var DIFF = {
    intro: { n: 4, label: "4×4 入门", scrambleMin: 40, scrambleMax: 80 },
    normal: { n: 5, label: "5×5 进阶", scrambleMin: 80, scrambleMax: 140 },
    hard: { n: 6, label: "6×6 挑战", scrambleMin: 120, scrambleMax: 220 },
  };
  var DIRS = [
    { dr: -1, dc: 0, key: "ArrowUp", opp: 1 },
    { dr: 1, dc: 0, key: "ArrowDown", opp: 0 },
    { dr: 0, dc: -1, key: "ArrowLeft", opp: 3 },
    { dr: 0, dc: 1, key: "ArrowRight", opp: 2 },
  ];

  var views = {
    home: document.getElementById("view-home"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result"),
  };
  var tierKey = "intro";
  var n = 4;
  var board = [];
  var blankIdx = 0;
  var moves = 0;
  var startedAt = 0;
  var timerId = null;
  var playing = false;
  var scrambleSeed = 0;

  function show(name) {
    Object.keys(views).forEach(function (k) {
      views[k].classList.toggle("hidden", k !== name);
    });
  }

  function fmtTime(ms) {
    ms = Math.max(0, ms | 0);
    var s = Math.floor(ms / 1000);
    var m = Math.floor(s / 60);
    s = s % 60;
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  function stopTimer() {
    if (timerId) clearInterval(timerId);
    timerId = null;
  }

  function updateTimer() {
    if (!startedAt) return;
    document.getElementById("ns-timer").textContent = fmtTime(Date.now() - startedAt);
  }

  function startTimer(anchorMs) {
    stopTimer();
    startedAt = anchorMs != null ? anchorMs : Date.now();
    timerId = setInterval(updateTimer, 200);
    updateTimer();
  }

  function solvedState(size) {
    var out = [];
    var i;
    for (i = 1; i < size * size; i++) out.push(i);
    out.push(0);
    return out;
  }

  function scrambleCount(cfg, seed) {
    var lo = cfg.scrambleMin;
    var hi = cfg.scrambleMax;
    var span = hi - lo + 1;
    var t = (seed >>> 0) || 1;
    t = Math.imul(t ^ (t >>> 15), 1 | t);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return lo + (((t ^ (t >>> 14)) >>> 0) % span);
  }

  function shuffleBoard(size, steps, seed) {
    var t = (seed >>> 0) || 1;
    function rnd() {
      t += 0x6d2b79f5;
      var r = Math.imul(t ^ (t >>> 15), 1 | t);
      r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    }
    var b = solvedState(size);
    var blank = size * size - 1;
    var lastDir = -1;
    var s;
    for (s = 0; s < steps; s++) {
      var r = Math.floor(blank / size);
      var c = blank % size;
      var options = [];
      var d;
      for (d = 0; d < DIRS.length; d++) {
        if (lastDir >= 0 && d === DIRS[lastDir].opp) continue;
        var nr = r + DIRS[d].dr;
        var nc = c + DIRS[d].dc;
        if (nr >= 0 && nr < size && nc >= 0 && nc < size) options.push(d);
      }
      if (!options.length) {
        for (d = 0; d < DIRS.length; d++) {
          var nr2 = r + DIRS[d].dr;
          var nc2 = c + DIRS[d].dc;
          if (nr2 >= 0 && nr2 < size && nc2 >= 0 && nc2 < size) options.push(d);
        }
      }
      var pick = options[Math.floor(rnd() * options.length)];
      var nr3 = r + DIRS[pick].dr;
      var nc3 = c + DIRS[pick].dc;
      var swapIdx = nr3 * size + nc3;
      b[blank] = b[swapIdx];
      b[swapIdx] = 0;
      blank = swapIdx;
      lastDir = pick;
    }
    return b;
  }

  function isSolved() {
    var target = solvedState(n);
    var i;
    for (i = 0; i < target.length; i++) {
      if (board[i] !== target[i]) return false;
    }
    return true;
  }

  function targetValueAt(idx) {
    return idx === n * n - 1 ? 0 : idx + 1;
  }

  function isTileSettled(idx) {
    return board[idx] === targetValueAt(idx);
  }

  function renderBoard() {
    var el = document.getElementById("ns-board");
    el.style.gridTemplateColumns = "repeat(" + n + ", minmax(0, 1fr))";
    el.style.gridTemplateRows = "repeat(" + n + ", minmax(0, 1fr))";
    el.innerHTML = "";
    var i;
    for (i = 0; i < board.length; i++) {
      var btn = document.createElement("button");
      btn.type = "button";
      var val = board[i];
      if (val === 0) {
        btn.className = "is-blank";
        btn.textContent = "";
        btn.disabled = true;
      } else {
        btn.textContent = String(val);
        btn.dataset.idx = String(i);
        if (isTileSettled(i)) {
          btn.classList.add("is-settled");
          btn.setAttribute("aria-label", val + " 已到位");
        }
        if (isAdjacentToBlank(i)) btn.classList.add("is-near");
        btn.addEventListener("click", function () {
          tryMove(Number(this.dataset.idx));
        });
      }
      el.appendChild(btn);
    }
  }

  function isAdjacentToBlank(idx) {
    var br = Math.floor(blankIdx / n);
    var bc = blankIdx % n;
    var r = Math.floor(idx / n);
    var c = idx % n;
    return (Math.abs(br - r) + Math.abs(bc - c)) === 1;
  }

  function tryMove(idx) {
    if (!playing || board[idx] === 0) return false;
    if (!isAdjacentToBlank(idx)) return false;
    board[blankIdx] = board[idx];
    board[idx] = 0;
    blankIdx = idx;
    moves += 1;
    document.getElementById("ns-moves").textContent = String(moves);
    renderBoard();
    if (isSolved()) finishRun();
    return true;
  }

  function moveByDir(dirIndex) {
    if (!playing) return;
    var br = Math.floor(blankIdx / n);
    var bc = blankIdx % n;
    var d = DIRS[dirIndex];
    var tr = br - d.dr;
    var tc = bc - d.dc;
    if (tr < 0 || tr >= n || tc < 0 || tc >= n) return;
    tryMove(tr * n + tc);
  }

  function preparePuzzle() {
    var cfg = DIFF[tierKey] || DIFF.intro;
    n = cfg.n;
    scrambleSeed = Date.now() ^ ((Math.random() * 0x7fffffff) | 0);
    var dq = window.__FGB_DAILY_Q__;
    if (dq && dq.seed) scrambleSeed = dq.seed >>> 0;
    var steps = scrambleCount(cfg, scrambleSeed);
    board = shuffleBoard(n, steps, scrambleSeed);
    blankIdx = board.indexOf(0);
    moves = 0;
    document.getElementById("play-label").textContent = cfg.label;
    document.getElementById("ns-moves").textContent = "0";
    document.getElementById("ns-timer").textContent = "00:00";
    renderBoard();
  }

  function beginPlay() {
    playing = false;
    stopTimer();
    startedAt = 0;
    show("play");
    var run = window.FGBUI && FGBUI.runWhenPlayable
      ? FGBUI.runWhenPlayable.bind(FGBUI)
      : function (prep, done) { prep(); done(Date.now()); };
    run(function () {
      preparePuzzle();
    }, function (t) {
      playing = true;
      startTimer(t);
    });
  }

  function finishRun() {
    playing = false;
    stopTimer();
    var elapsed = Date.now() - startedAt;
    var cfg = DIFF[tierKey] || DIFF.intro;
    document.getElementById("st-size").textContent = cfg.n + "×" + cfg.n;
    document.getElementById("st-moves").textContent = String(moves);
    document.getElementById("st-time").textContent = fmtTime(elapsed);
    document.getElementById("result-sub").textContent =
      moves <= 80 ? "很利索！" : "完成还原，不错！";
    show("result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") {
      fgbSubmitScore({
        gameId: "number-slide",
        mode: "challenge",
        tier: tierKey,
        tierLabel: cfg.label,
        metrics: {
          timeMs: elapsed,
          moves: moves,
          done: 1,
          total: 1,
        },
      });
    }
  }

  document.querySelectorAll("#tier-pick .ns-tier-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#tier-pick .ns-tier-btn").forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      tierKey = btn.getAttribute("data-tier") || "intro";
    });
  });

  document.getElementById("btn-start").addEventListener("click", beginPlay);
  document.getElementById("btn-again").addEventListener("click", beginPlay);
  document.getElementById("btn-restart").addEventListener("click", beginPlay);
  document.getElementById("btn-home").addEventListener("click", function () {
    stopTimer();
    show("home");
  });
  document.getElementById("btn-exit").addEventListener("click", function () {
    if (window.__FGB_IS_DAILY__ || /(?:^|[?&])daily=1(?:&|$)/.test(location.search || "")) {
      if (window.FGBDaily && FGBDaily.notifyAbort) FGBDaily.notifyAbort();
      return;
    }
    askConfirm("确定退出？本局不会记入成绩。", function () {
      stopTimer();
      show("home");
    });
  });

  document.addEventListener("keydown", function (e) {
    if (views.play.classList.contains("hidden") || !playing) return;
    var map = { ArrowUp: 0, ArrowDown: 1, ArrowLeft: 2, ArrowRight: 3 };
    if (map[e.key] == null) return;
    e.preventDefault();
    moveByDir(map[e.key]);
  });

  if (window.__FGB_IS_DAILY__ || /(?:^|[?&])daily=1(?:&|$)/.test(location.search || "")) {
    var dq = window.__FGB_DAILY_Q__ || {};
    if (!dq.tier) dq.tier = (new URLSearchParams(location.search || "")).get("tier") || "intro";
    if (dq.tier && DIFF[dq.tier]) tierKey = dq.tier;
    beginPlay();
  } else {
    show("home");
  }
})();
"""


def build_html() -> str:
    return build_page(
        "数字华容道",
        EXTRA_CSS,
        inject_lobby_link(BODY),
        SCRIPT,
        wide=True,
        game_skin="number-slide",
        game_title="数字华容道",
    )


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate 数字华容道 HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
