#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成数字/汉字划销训练页 cancel.html。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator, tier_choice_row
from common.paths import game_page_paths

SLUG = "cancel"

CANCEL_TIER_SUB = {
    "intro": "8×8",
    "simple": "10×10",
    "normal": "12×12",
    "hard": "14×14",
    "master": "16×16",
    "god": "18×18",
}

HANZI_POOL = (
    "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工"
    "也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小"
    "物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相"
    "全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月"
    "公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求"
    "老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回"
)

EXTRA_CSS = r"""
.target-bar {
  text-align: center;
  font-size: 1.15rem;
  margin-bottom: .65rem;
}
.target-bar strong {
  font-family: var(--display);
  font-size: 1.6rem;
  color: var(--accent-deep);
}
.grid-wrap { overflow-x: auto; }
.grid-cells.dense button {
  min-height: 40px;
  font-size: clamp(1rem, 3.6vw, 1.35rem);
  font-weight: 700;
}
.target-bar strong {
  color: var(--accent);
}
"""

BODY = r"""
  <section id="view-home">
    <h1>划销<em>训练</em></h1>
    <p class="sub">在矩阵中找出所有目标数字或汉字并点击标记。难度由格子规模决定。</p>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-casual">
        <strong>休闲模式</strong>
        <span>自选规模与题型，找齐后下一题</span>
      </button>
      <button type="button" class="mode-btn" id="btn-challenge">
        <strong>挑战模式</strong>
        <span>固定规模连做，统计误点与用时</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-casual" class="hidden">
    <h1>休闲</h1>
    <p class="sub">选择题型与格子规模。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">题型</p>
      <div class="choice-row two" id="casual-type">
        <button type="button" data-type="digit" class="active">数字</button>
        <button type="button" data-type="hanzi">汉字</button>
      </div>
      <p style="margin:1rem 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("casual-diff", CANCEL_TIER_SUB) + r"""
      <button type="button" class="primary" id="btn-casual-start">开始</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-casual-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-setup" class="hidden">
    <h1>挑战</h1>
    <p class="sub">选择题型、规模与题量。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">题型</p>
      <div class="choice-row two" id="type-choices">
        <button type="button" data-type="digit" class="active">数字</button>
        <button type="button" data-type="hanzi">汉字</button>
      </div>
      <p style="margin:1rem 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("diff-choices", CANCEL_TIER_SUB) + r"""
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
      <span id="play-timer"><strong id="timer-text">00:00</strong></span>
    </div>
    <div class="target-bar">请找出所有的：<strong id="target-display">7</strong></div>
    <p class="hint" id="play-hint">点击目标格进行划销</p>
    <div class="card">
      <div class="grid-wrap">
        <div class="grid-cells dense" id="grid"></div>
      </div>
      <div class="actions">
        <button type="button" class="danger" id="btn-exit">退出</button>
        <button type="button" id="btn-restart">重来</button>
        <button type="button" id="btn-done">完成</button>
      </div>
      <div class="actions two" id="casual-extra">
        <button type="button" class="ghost" id="btn-next" style="grid-column:1/-1">下一题</button>
      </div>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>结算</h1>
    <p class="sub" id="result-sub">本局挑战结束</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>题量</span><strong id="st-rounds">0</strong></li>
        <li><span>规模</span><strong id="st-size">10×10</strong></li>
        <li><span>完成</span><strong id="st-done">0</strong></li>
        <li><span>总用时</span><strong id="st-time">00:00</strong></li>
        <li><span>误点</span><strong id="st-wrong">0</strong></li>
        <li><span>漏划</span><strong id="st-miss">0</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>
"""

SCRIPT_PREFIX = r"""
(function () {
  var HANZI = """
SCRIPT_MID = r""";
  var views = {
    home: document.getElementById("view-home"),
    casual: document.getElementById("view-casual"),
    setup: document.getElementById("view-setup"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result")
  };

  var mode = "casual";
  var puzzleType = "digit";
  var diffKey = "normal";
  var challengeTotal = 5;
  var roundIndex = 0;
  var roundsDone = 0;
  var totalWrong = 0;
  var totalMiss = 0;
  var startedAt = 0;
  var roundStart = 0;
  var timerId = null;

  var puzzle = null;
  var marked = {};
  var frozenUntil = 0;

  var DIFF = {
    intro: { size: 8, pct: 0.12, label: "入门" },
    simple: { size: 10, pct: 0.11, label: "简单" },
    normal: { size: 12, pct: 0.10, label: "普通" },
    hard: { size: 14, pct: 0.09, label: "困难" },
    master: { size: 16, pct: 0.07, label: "大师" },
    god: { size: 18, pct: 0.06, label: "大神" }
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
    FGB.loadDifficulty("cancel").then(function (cfg) {
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
  function updateTimer() {
    document.getElementById("timer-text").textContent = fmtTime(Date.now() - startedAt);
  }
  function startTimer() {
    stopTimer();
    timerId = setInterval(updateTimer, 500);
    updateTimer();
  }

  function pickTargetDigit() {
    return String(randInt(10));
  }
  function pickTargetHanzi() {
    return HANZI.charAt(randInt(HANZI.length));
  }
  function pickFillDigit(exclude) {
    var d;
    do { d = String(randInt(10)); } while (d === exclude);
    return d;
  }
  function pickFillHanzi(exclude) {
    var c;
    do { c = HANZI.charAt(randInt(HANZI.length)); } while (c === exclude);
    return c;
  }

  function genPuzzle(type) {
    var diff = DIFF[diffKey] || DIFF.normal;
    var n = diff.size;
    var target = type === "digit" ? pickTargetDigit() : pickTargetHanzi();
    var count = Math.max(3, Math.round(n * n * diff.pct));
    var cells = [];
    var targets = {};
    var positions = [];
    for (var r = 0; r < n; r++) {
      for (var c = 0; c < n; c++) positions.push(r * n + c);
    }
    positions = shuffle(positions);
    for (var i = 0; i < count; i++) targets[positions[i]] = true;
    for (var i = 0; i < n * n; i++) {
      if (targets[i]) cells.push(target);
      else cells.push(type === "digit" ? pickFillDigit(target) : pickFillHanzi(target));
    }
    return { n: n, target: target, type: type, cells: cells, targetCount: count };
  }

  function modeLabel() {
    var d = DIFF[diffKey];
    return (mode === "casual" ? "休闲" : "挑战")
      + " · " + (puzzleType === "digit" ? "数字" : "汉字")
      + " · " + diffLabel(diffKey);
  }

  function renderGrid() {
    var grid = document.getElementById("grid");
    grid.style.gridTemplateColumns = "repeat(" + puzzle.n + ", 1fr)";
    grid.innerHTML = "";
    marked = {};
    for (var i = 0; i < puzzle.cells.length; i++) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = puzzle.cells[i];
      btn.dataset.i = String(i);
      btn.addEventListener("click", function () { onCellClick(Number(this.dataset.i), this); });
      grid.appendChild(btn);
    }
    document.getElementById("target-display").textContent = puzzle.target;
    document.getElementById("found-n").textContent = "0";
    document.getElementById("total-n").textContent = String(puzzle.targetCount);
    document.getElementById("play-hint").className = "hint";
    document.getElementById("play-hint").textContent = "点击目标格进行划销";
  }

  function isTarget(i) {
    return puzzle.cells[i] === puzzle.target;
  }

  function foundCount() {
    var n = 0;
    Object.keys(marked).forEach(function (k) { if (marked[k]) n++; });
    return n;
  }

  function onCellClick(i, el) {
    if (Date.now() < frozenUntil || marked[i]) return;
    if (isTarget(i)) {
      marked[i] = true;
      el.classList.add("marked");
      var fc = foundCount();
      document.getElementById("found-n").textContent = String(fc);
      if (fc >= puzzle.targetCount) onRoundComplete(false);
    } else {
      totalWrong++;
      el.classList.add("wrong-flash");
      frozenUntil = Date.now() + 500;
      document.getElementById("play-hint").className = "hint err";
      document.getElementById("play-hint").textContent = "点错了，再找找";
    }
  }

  function onRoundComplete(skipped) {
    if (!skipped) {
      roundsDone++;
    } else {
      var miss = puzzle.targetCount - foundCount();
      totalMiss += miss;
    }
    if (mode === "challenge") {
      roundIndex++;
      document.getElementById("play-progress").textContent =
        roundIndex + " / " + challengeTotal;
      if (roundIndex >= challengeTotal) {
        celebrateThen(FGB_MSG.sessionDone, finishChallenge, 500);
      } else {
        celebrateThen(FGB_MSG.done, loadRound, 480);
      }
    } else {
      celebrate(FGB_MSG.done);
      document.getElementById("play-hint").className = "hint ok";
      document.getElementById("play-hint").textContent = "找齐了！可点下一题";
      if (typeof fgbSubmitScore === "function") fgbSubmitScore({
        gameId: "cancel", mode: "casual", tier: diffKey,
        metrics: { timeMs: Date.now() - roundStart, correct: 1, total: 1 }
      });
    }
  }

  function loadRound() {
    roundStart = Date.now();
    puzzle = genPuzzle(puzzleType);
    renderGrid();
  }

  function startCasual() {
    ensureDifficulty(function () {
      mode = "casual";
      stopTimer();
      document.getElementById("play-label").textContent = modeLabel();
      document.getElementById("play-progress").textContent = "";
      document.getElementById("timer-text").textContent = "—";
      document.getElementById("casual-extra").classList.remove("hidden");
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
      totalMiss = 0;
      startedAt = Date.now();
      document.getElementById("play-label").textContent = modeLabel();
      document.getElementById("casual-extra").classList.add("hidden");
      showView(views, "play");
      startTimer();
      loadRound();
    });
  }

  function finishChallenge() {
    stopTimer();
    var d = DIFF[diffKey];
    document.getElementById("st-rounds").textContent = String(challengeTotal);
    document.getElementById("st-size").textContent = d.size + "×" + d.size;
    document.getElementById("st-done").textContent = String(roundsDone);
    document.getElementById("st-time").textContent = fmtTime(Date.now() - startedAt);
    document.getElementById("st-wrong").textContent = String(totalWrong);
    document.getElementById("st-miss").textContent = String(totalMiss);
    showView(views, "result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") {
      fgbSubmitScore({
        gameId: "cancel", mode: "challenge", tier: diffKey,
        metrics: {
          correct: roundsDone, total: challengeTotal, timeMs: Date.now() - startedAt,
          wrong: totalWrong, miss: totalMiss
        }
      });
    }
  }

  function bindChoice(selector, onPick) {
    document.querySelectorAll(selector).forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(selector).forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        onPick(btn);
      });
    });
  }

  document.getElementById("btn-casual").addEventListener("click", function () { showView(views, "casual"); });
  document.getElementById("btn-challenge").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-casual-back").addEventListener("click", function () { showView(views, "home"); });
  document.getElementById("btn-setup-back").addEventListener("click", function () { showView(views, "home"); });
  bindChoice("#casual-type button", function (btn) { puzzleType = btn.dataset.type; });
  bindChoice("#type-choices button", function (btn) { puzzleType = btn.dataset.type; });
  bindChoice("#casual-diff button", function (btn) { diffKey = btn.dataset.diff; });
  bindChoice("#diff-choices button", function (btn) { diffKey = btn.dataset.diff; });
  bindChoice("#count-choices button", function (btn) { challengeTotal = Number(btn.dataset.n); });
  document.getElementById("btn-casual-start").addEventListener("click", startCasual);
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
  document.getElementById("btn-restart").addEventListener("click", renderGrid);
  document.getElementById("btn-done").addEventListener("click", function () {
    var miss = puzzle.targetCount - foundCount();
    if (miss > 0) {
      totalMiss += miss;
      document.getElementById("play-hint").className = "hint err";
      document.getElementById("play-hint").textContent = "还有 " + miss + " 个未找到";
      if (mode === "challenge") {
        roundIndex++;
        if (roundIndex >= challengeTotal) finishChallenge();
        else loadRound();
      }
      return;
    }
    onRoundComplete(false);
  });
  document.getElementById("btn-next").addEventListener("click", loadRound);
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
    hanzi_json = json.dumps(HANZI_POOL, ensure_ascii=False)
    script = SCRIPT_PREFIX + hanzi_json + SCRIPT_MID
    return build_page("划销训练", EXTRA_CSS, inject_lobby_link(BODY), script, wide=True)


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate cancel training HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
