#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成找不同（符号矩阵）训练页 spot_diff.html。"""

from __future__ import annotations

import argparse
import json

import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator, tier_choice_row
from common.paths import game_page_paths

SLUG = "spot-diff"

SPOT_DIFF_TIER_SUB = {
    "intro": "5×5 · 3 处",
    "simple": "6×6 · 4 处",
    "normal": "7×7 · 5 处",
    "hard": "8×8 · 6 处",
    "master": "9×9 · 8 处",
    "god": "10×10 · 10 处",
}

CHARS = "0123456789"

EXTRA_CSS = r"""
.diff-panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .65rem;
  align-items: start;
}
@media (max-width: 520px) {
  .diff-panels { grid-template-columns: 1fr; }
}
.diff-panel {
  border-radius: 14px;
  padding: .55rem .5rem .65rem;
  min-width: 0;
}
.diff-panel.left {
  background: rgba(15, 122, 90, 0.1);
  border: 1px solid rgba(15, 122, 90, 0.22);
}
.diff-panel.right {
  background: rgba(154, 74, 18, 0.1);
  border: 1px solid rgba(154, 74, 18, 0.22);
}
.panel-label {
  text-align: center;
  font-size: .85rem;
  font-weight: 700;
  margin-bottom: .4rem;
}
.diff-panel.left .panel-label { color: var(--accent-deep); }
.diff-panel.right .panel-label { color: var(--warn); }
.diff-panel .grid-cells.compact {
  width: min(100%, 42vmin, 420px);
  margin: 0 auto;
  container-type: inline-size;
}
.grid-cells.compact button {
  min-height: 0;
  aspect-ratio: 1;
  font-size: clamp(.7rem, 8cqi, 1.15rem);
  font-weight: 700;
  border-radius: 6px;
}
@media (max-height: 720px), (orientation: landscape) and (max-height: 900px) {
  .diff-panels { gap: .45rem; }
  .diff-panel { padding: .35rem .35rem .45rem; }
  .panel-label { margin-bottom: .25rem; font-size: .78rem; }
  /* 双栏各占短边约四成，横屏放宽上限而不是再压小 */
  .diff-panel .grid-cells.compact { width: min(100%, 44vmin, 460px); }
}
"""

BODY = r"""
  <section id="view-home">
    <h1>找<em>不同</em></h1>
    <p class="sub">对比左右两图，点击差异格。符号矩阵版，训练细致观察与系统扫描。</p>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-casual">
        <strong>休闲模式</strong>
        <span>自选规模，随机一题，可提示</span>
      </button>
      <button type="button" class="mode-btn" id="btn-challenge">
        <strong>挑战模式</strong>
        <span>固定规模连做，累计误点</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-casual" class="hidden">
    <h1>休闲</h1>
    <p class="sub">选择难度（矩阵规模与差异数）。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("casual-diff", SPOT_DIFF_TIER_SUB) + r"""
      <button type="button" class="primary" id="btn-casual-start">开始</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-casual-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-setup" class="hidden">
    <h1>挑战</h1>
    <p class="sub">选择难度与题量。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("diff-choices", SPOT_DIFF_TIER_SUB) + r"""
      <p style="margin:1rem 0 .5rem;color:var(--muted);font-size:.9rem">题量</p>
      <div class="choice-row" id="count-choices">
        <button type="button" data-n="5" class="active">5 题</button>
        <button type="button" data-n="10">10 题</button>
        <button type="button" data-n="15">15 题</button>
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
      <span>已找 <strong id="found-n">0</strong> / <strong id="total-n">0</strong></span>
      <span><strong id="timer-text">00:00</strong></span>
    </div>
    <p class="hint" id="play-hint">点击任一侧的差异格</p>
    <div class="card">
      <div class="diff-panels">
        <div class="diff-panel left">
          <div class="panel-label">左图</div>
          <div class="grid-cells compact" id="grid-left"></div>
        </div>
        <div class="diff-panel right">
          <div class="panel-label">右图</div>
          <div class="grid-cells compact" id="grid-right"></div>
        </div>
      </div>
      <div class="actions">
        <button type="button" class="danger" id="btn-exit">退出</button>
        <button type="button" id="btn-hint">提示</button>
        <button type="button" id="btn-restart">重来</button>
      </div>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>结算</h1>
    <p class="sub">本局挑战结束</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>题量</span><strong id="st-rounds">0</strong></li>
        <li><span>完成</span><strong id="st-done">0</strong></li>
        <li><span>总用时</span><strong id="st-time">00:00</strong></li>
        <li><span>误点</span><strong id="st-wrong">0</strong></li>
        <li><span>提示</span><strong id="st-hints">0</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>
"""

SCRIPT_PREFIX = r"""
(function () {
  var CHARS = """
SCRIPT_MID = r""";
  var views = {
    home: document.getElementById("view-home"),
    casual: document.getElementById("view-casual"),
    setup: document.getElementById("view-setup"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result")
  };

  var mode = "casual";
  var challengeTotal = 5;
  var roundIndex = 0;
  var roundStart = 0;
  var roundsDone = 0;
  var totalWrong = 0;
  var totalHints = 0;
  var hintsLeft = 2;
  var startedAt = 0;
  var timerId = null;
  var puzzle = null;
  var found = {};
  var frozenUntil = 0;
  var diffKey = "normal";

  var DIFF = {
    intro: { n: 5, diffs: 3, label: "入门" },
    simple: { n: 6, diffs: 4, label: "简单" },
    normal: { n: 7, diffs: 5, label: "普通" },
    hard: { n: 8, diffs: 6, label: "困难" },
    master: { n: 9, diffs: 8, label: "大师" },
    god: { n: 10, diffs: 10, label: "大神" }
  };

  function mergeDifficultyConfig(cfg) {
    if (!cfg || !cfg.tiers) return;
    Object.keys(cfg.tiers).forEach(function (k) {
      if (!DIFF[k]) return;
      Object.assign(DIFF[k], cfg.tiers[k]);
    });
  }
  function ensureDifficulty(thenFn) {
    if (!window.FGB || !FGB.loadDifficulty) { thenFn(); return; }
    FGB.loadDifficulty("spot-diff").then(function (cfg) {
      mergeDifficultyConfig(cfg);
      thenFn();
    });
  }

  function diffLabel(key) {
    var d = DIFF[key];
    return d ? d.label : key;
  }

  function stopTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }
  function startTimer() {
    stopTimer();
    timerId = setInterval(function () {
      document.getElementById("timer-text").textContent = fmtTime(Date.now() - startedAt);
    }, 500);
  }

  var currentDiff = "normal";

  function bindDiffChoice(selector, onPick) {
    document.querySelectorAll(selector).forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(selector).forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        diffKey = btn.dataset.diff;
        currentDiff = diffKey;
        if (onPick) onPick(btn);
      });
    });
  }

  function genPuzzle() {
    var d = DIFF[diffKey] || DIFF.intro;
    currentDiff = diffKey;
    var n = d.n;
    var left = [];
    for (var i = 0; i < n * n; i++) left.push(CHARS.charAt(randInt(CHARS.length)));
    var right = left.slice();
    var diffSet = {};
    var positions = [];
    for (var i = 0; i < n * n; i++) positions.push(i);
    positions = shuffle(positions);
    for (var k = 0; k < d.diffs; k++) {
      var p = positions[k];
      diffSet[p] = true;
      var c;
      do { c = CHARS.charAt(randInt(CHARS.length)); } while (c === left[p]);
      right[p] = c;
    }
    return { n: n, left: left, right: right, diffs: Object.keys(diffSet).map(Number), diffSet: diffSet };
  }

  function renderSide(el, data, side) {
    el.style.gridTemplateColumns = "repeat(" + puzzle.n + ", 1fr)";
    el.innerHTML = "";
    for (var i = 0; i < data.length; i++) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = data[i];
      btn.dataset.i = String(i);
      btn.dataset.side = side;
      if (found[i]) btn.classList.add("found");
      btn.addEventListener("click", onCellClick);
      el.appendChild(btn);
    }
  }

  function render() {
    renderSide(document.getElementById("grid-left"), puzzle.left, "L");
    renderSide(document.getElementById("grid-right"), puzzle.right, "R");
    document.getElementById("found-n").textContent = String(Object.keys(found).length);
    document.getElementById("total-n").textContent = String(puzzle.diffs.length);
  }

  function onCellClick() {
    var i = Number(this.dataset.i);
    if (Date.now() < frozenUntil || found[i]) return;
    if (puzzle.diffSet[i]) {
      found[i] = true;
      render();
      document.getElementById("play-hint").className = "hint ok";
      document.getElementById("play-hint").textContent = "找到了！";
      if (Object.keys(found).length >= puzzle.diffs.length) onRoundDone();
    } else {
      totalWrong++;
      this.classList.add("wrong-flash");
      frozenUntil = Date.now() + 800;
      document.getElementById("play-hint").className = "hint err";
      document.getElementById("play-hint").textContent = "这里没有差异";
    }
  }

  function onRoundDone() {
    roundsDone++;
    if (mode === "challenge") {
      roundIndex++;
      if (roundIndex >= challengeTotal) {
        celebrateThen(FGB_MSG.sessionDone, finishChallenge, 500);
      } else {
        celebrateThen(FGB_MSG.done, loadRound, 480);
      }
    } else {
      celebrate(FGB_MSG.done);
      if (typeof fgbSubmitScore === "function") fgbSubmitScore({
        gameId: "spot-diff", mode: "casual", tier: currentDiff,
        metrics: { timeMs: Date.now() - roundStart, correct: 1, total: 1 }
      });
    }
  }

  function loadRound() {
    roundStart = Date.now();
    found = {};
    hintsLeft = mode === "challenge" ? 1 : 2;
    puzzle = genPuzzle();
    render();
    document.getElementById("play-progress").textContent =
      mode === "challenge" ? (roundIndex + 1 + " / " + challengeTotal) : "";
    document.getElementById("play-hint").className = "hint";
    document.getElementById("play-hint").textContent = "点击任一侧的差异格";
  }

  function startCasual() {
    ensureDifficulty(function () {
      mode = "casual";
      stopTimer();
      document.getElementById("play-label").textContent = "休闲 · " + diffLabel(diffKey);
      document.getElementById("timer-text").textContent = "—";
      showView(views, "play");
      loadRound();
    });
  }

  function startChallenge() {
    ensureDifficulty(function () {
      mode = "challenge";
      roundIndex = 0;
      roundsDone = 0;
      totalWrong = 0;
      totalHints = 0;
      startedAt = Date.now();
      document.getElementById("play-label").textContent = "挑战 · " + diffLabel(diffKey);
      showView(views, "play");
      startTimer();
      loadRound();
    });
  }

  function finishChallenge() {
    stopTimer();
    document.getElementById("st-rounds").textContent = String(challengeTotal);
    document.getElementById("st-done").textContent = String(roundsDone);
    document.getElementById("st-time").textContent = fmtTime(Date.now() - startedAt);
    document.getElementById("st-wrong").textContent = String(totalWrong);
    document.getElementById("st-hints").textContent = String(totalHints);
    showView(views, "result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") fgbSubmitScore({
      gameId: "spot-diff", mode: "challenge", tier: currentDiff,
      metrics: {
        done: roundsDone, total: challengeTotal,
        timeMs: Date.now() - startedAt, wrong: totalWrong
      }
    });
  }

  document.getElementById("btn-casual").addEventListener("click", function () { showView(views, "casual"); });
  document.getElementById("btn-casual-back").addEventListener("click", function () { showView(views, "home"); });
  document.getElementById("btn-casual-start").addEventListener("click", startCasual);
  document.getElementById("btn-challenge").addEventListener("click", function () { showView(views, "setup"); });
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
  document.getElementById("btn-start").addEventListener("click", startChallenge);
  document.getElementById("btn-exit").addEventListener("click", function () {
    function doExit() {
      stopTimer();
      if (mode === "challenge" && roundIndex > 0) finishChallenge();
      else showView(views, "home");
    }
    if (mode === "challenge" && roundIndex > 0) {
      askConfirm(FGB_MSG.exitConfirm, doExit);
      return;
    }
    doExit();
  });
  document.getElementById("btn-hint").addEventListener("click", function () {
    if (hintsLeft <= 0) return;
    var remain = puzzle.diffs.filter(function (p) { return !found[p]; });
    if (!remain.length) return;
    var p = remain[randInt(remain.length)];
    found[p] = true;
    hintsLeft--;
    totalHints++;
    render();
    if (Object.keys(found).length >= puzzle.diffs.length) onRoundDone();
  });
  document.getElementById("btn-restart").addEventListener("click", function () {
    found = {};
    render();
  });
  document.getElementById("btn-again").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-home").addEventListener("click", function () { stopTimer(); showView(views, "home"); });

  ensureDifficulty(function () {
    if (window.__FGB_IS_DAILY__ || /(?:^|[?&])daily=1(?:&|$)/.test(location.search || "")) {
      var dq = window.__FGB_DAILY_Q__ || {};
      if (!dq.tier) dq.tier = (new URLSearchParams(location.search || "")).get("tier") || "normal";
      if (dq.tier && DIFF[dq.tier]) diffKey = dq.tier;
      startCasual();
    } else {
      showView(views, "home");
    }
  });
})();
"""


def build_html() -> str:
    chars_json = json.dumps(CHARS)
    script = SCRIPT_PREFIX + chars_json + SCRIPT_MID
    return build_page("找不同", EXTRA_CSS, inject_lobby_link(BODY), script, wide=True)


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate spot-the-difference HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
