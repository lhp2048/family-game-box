#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Stroop 色字干扰训练页 stroop.html。"""

from __future__ import annotations

import argparse
from pathlib import Path

import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator, tier_choice_row
from common.paths import game_page_paths

SLUG = "stroop"

STROOP_TIER_SUB = {
    "intro": "20 试次",
    "simple": "30 试次",
    "normal": "60 秒",
    "hard": "90 秒",
    "master": "50 试次",
    "god": "120 秒",
}

EXTRA_CSS = r"""
.stroop-word {
  font-family: var(--display);
  font-size: clamp(3rem, 14vw, 4.5rem);
  font-weight: 800;
  text-align: center;
  margin: 1.2rem 0 1.4rem;
  line-height: 1.1;
  min-height: 1.2em;
  -webkit-text-stroke: 0.5px rgba(0,0,0,.12);
}
.color-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: .55rem;
}
.color-grid button {
  border: 2px solid var(--line);
  border-radius: 14px;
  padding: .85rem .2rem;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  min-height: 48px;
  transition: transform .12s ease;
}
.color-grid button:hover { transform: translateY(-1px); }
.color-grid button:disabled { opacity: .45; cursor: not-allowed; transform: none; }
.stat-row {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: .9rem;
  margin-top: .75rem;
}
.stat-row strong { color: var(--ink); }
@media (max-height: 720px), (orientation: landscape) and (max-height: 900px) {
  .stroop-word {
    font-size: clamp(2.2rem, 8vw, 3.2rem);
    margin: .55rem 0 .7rem;
  }
  .color-grid button { padding: .6rem .15rem; min-height: 42px; }
  .stat-row { margin-top: .4rem; gap: .65rem; font-size: .82rem; }
}
"""

BODY = r"""
  <section id="view-home">
    <h1>Stroop<em>色字</em></h1>
    <p class="sub">快速选出字的颜色，不要读字义。经典认知训练，锻炼抗干扰与选择性注意。</p>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-casual">
        <strong>休闲模式</strong>
        <span>无限练习，即时反馈，不计时</span>
      </button>
      <button type="button" class="mode-btn" id="btn-challenge">
        <strong>挑战模式</strong>
        <span>限时或固定试次，结束后看 Stroop 干扰量</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-casual" class="hidden">
    <h1>休闲</h1>
    <p class="sub">选择难度后开始练习。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("casual-diff", STROOP_TIER_SUB) + r"""
      <button type="button" class="primary" id="btn-casual-start">开始</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-casual-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-setup" class="hidden">
    <h1>挑战</h1>
    <p class="sub">选择难度后开始挑战。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("diff-choices", STROOP_TIER_SUB) + r"""
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
    <div class="task-bar" id="task-bar">请选字的颜色，不要读字</div>
    <p class="hint" id="play-hint">看颜色，点下方色块</p>
    <div class="card">
      <div class="stroop-word" id="stroop-word">—</div>
      <div class="color-grid" id="color-grid"></div>
      <div class="stat-row">
        <span>连击 <strong id="streak">0</strong></span>
        <span>正确 <strong id="correct-n">0</strong></span>
        <span id="rt-display"></span>
      </div>
      <div class="actions">
        <button type="button" class="danger" id="btn-exit">退出</button>
        <button type="button" id="btn-next">下一题</button>
      </div>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>结算</h1>
    <p class="sub" id="result-sub">本局挑战结束</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>试次</span><strong id="st-total">0</strong></li>
        <li><span>正确</span><strong id="st-correct">0</strong></li>
        <li><span>正确率</span><strong id="st-rate">0%</strong></li>
        <li><span>用时</span><strong id="st-time">00:00</strong></li>
        <li><span>平均反应时</span><strong id="st-rt">—</strong></li>
        <li><span>一致试次 RT</span><strong id="st-rt-cong">—</strong></li>
        <li><span>不一致试次 RT</span><strong id="st-rt-incong">—</strong></li>
        <li><span>Stroop 干扰量</span><strong id="st-interference">—</strong></li>
        <li><span>最长连击</span><strong id="st-streak">0</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>
"""

SCRIPT = r"""
(function () {
  var COLORS = [
    { id: "red", label: "红", hex: "#c0392b" },
    { id: "yellow", label: "黄", hex: "#c9a227" },
    { id: "blue", label: "蓝", hex: "#2471a3" },
    { id: "green", label: "绿", hex: "#1e8449" },
    { id: "black", label: "黑", hex: "#1a2421" },
    { id: "purple", label: "紫", hex: "#7d3c98" },
    { id: "orange", label: "橙", hex: "#d35400" },
    { id: "white", label: "白", hex: "#ecf0f1" }
  ];
  var byId = {};
  COLORS.forEach(function (c) { byId[c.id] = c; });

  var views = {
    home: document.getElementById("view-home"),
    casual: document.getElementById("view-casual"),
    setup: document.getElementById("view-setup"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result")
  };

  var mode = "casual";
  var diffKey = "normal";
  var DIFF = {
    intro: { label: "入门", trialLimit: 20, timeLimitMs: 0, congruentRate: 0.35 },
    simple: { label: "简单", trialLimit: 30, timeLimitMs: 0, congruentRate: 0.28 },
    normal: { label: "普通", trialLimit: 0, timeLimitMs: 60000, congruentRate: 0.2 },
    hard: { label: "困难", trialLimit: 0, timeLimitMs: 90000, congruentRate: 0.15 },
    master: { label: "大师", trialLimit: 50, timeLimitMs: 0, congruentRate: 0.12 },
    god: { label: "大神", trialLimit: 0, timeLimitMs: 120000, congruentRate: 0.1 }
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
    FGB.loadDifficulty("stroop").then(function (cfg) {
      mergeDifficultyConfig(cfg);
      thenFn();
    });
  }

  function diffLabel(key) {
    var d = DIFF[key];
    return d ? d.label : key;
  }

  function applyDiff() {
    var d = DIFF[diffKey] || DIFF.normal;
    trialLimit = d.trialLimit;
    timeLimitMs = d.timeLimitMs;
    congruentRate = d.congruentRate;
  }

  var trialLimit = 0;
  var timeLimitMs = 0;
  var congruentRate = 0.2;
  var deadline = 0;
  var timerId = null;
  var startedAt = 0;
  var trialStart = 0;
  var waiting = false;
  var currentTrial = null;

  var total = 0;
  var correct = 0;
  var streak = 0;
  var maxStreak = 0;
  var rts = [];
  var rtsCong = [];
  var rtsIncong = [];

  var wordEl = document.getElementById("stroop-word");
  var gridEl = document.getElementById("color-grid");
  var hintEl = document.getElementById("play-hint");
  var progressEl = document.getElementById("play-progress");
  var labelEl = document.getElementById("play-label");

  function avg(arr) {
    if (!arr.length) return null;
    var s = 0;
    for (var i = 0; i < arr.length; i++) s += arr[i];
    return Math.round(s / arr.length);
  }

  function fmtMs(v) {
    return v == null ? "—" : v + " ms";
  }

  function stopTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }

  function updateTimer() {
    var left = Math.max(0, deadline - Date.now());
    document.getElementById("timer-text").textContent = fmtTime(left);
    if (left <= 0 && mode === "challenge" && timeLimitMs > 0) finishChallenge();
  }

  function startTimer() {
    stopTimer();
    timerId = setInterval(updateTimer, 200);
    updateTimer();
  }

  function resetStats() {
    total = 0; correct = 0; streak = 0; maxStreak = 0;
    rts = []; rtsCong = []; rtsIncong = [];
    document.getElementById("streak").textContent = "0";
    document.getElementById("correct-n").textContent = "0";
    document.getElementById("rt-display").textContent = "";
  }

  function buildTrial() {
    var wordColor = pick(COLORS);
    var congruent = Math.random() < congruentRate;
    var inkColor = congruent ? wordColor : pick(COLORS.filter(function (c) { return c.id !== wordColor.id; }));
    var choices = shuffle(COLORS.slice()).slice(0, 4);
    if (!choices.some(function (c) { return c.id === inkColor.id; })) {
      choices[0] = inkColor;
    }
    return { word: wordColor.label, inkId: inkColor.id, inkHex: inkColor.hex, congruent: congruent, choices: choices };
  }

  function renderChoices(choices, disabled) {
    gridEl.innerHTML = "";
    choices.forEach(function (c) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = c.label;
      btn.style.background = c.hex;
      btn.style.color = (c.id === "white" || c.id === "yellow") ? "#1a2421" : "#fff";
      btn.style.borderColor = c.hex;
      btn.disabled = !!disabled;
      btn.dataset.id = c.id;
      btn.addEventListener("click", function () { onAnswer(c.id); });
      gridEl.appendChild(btn);
    });
  }

  function showTrial() {
    waiting = true;
    currentTrial = buildTrial();
    wordEl.textContent = currentTrial.word;
    wordEl.style.color = currentTrial.inkHex;
    if (currentTrial.inkId === "white") wordEl.style.textShadow = "0 0 1px #888";
    else wordEl.style.textShadow = "none";
    renderChoices(currentTrial.choices, false);
    hintEl.className = "hint";
    hintEl.textContent = "看颜色，点下方色块";
    trialStart = performance.now();
    waiting = false;
  }

  function setHint(text, cls) {
    hintEl.textContent = text;
    hintEl.className = "hint" + (cls ? " " + cls : "");
  }

  function onAnswer(choiceId) {
    if (waiting || !currentTrial) return;
    waiting = true;
    renderChoices(currentTrial.choices, true);
    var rt = Math.round(performance.now() - trialStart);
    total++;
    var ok = choiceId === currentTrial.inkId;
    if (ok) {
      correct++;
      streak++;
      if (streak > maxStreak) maxStreak = streak;
      rts.push(rt);
      if (currentTrial.congruent) rtsCong.push(rt); else rtsIncong.push(rt);
      setHint("正确 · " + rt + " ms", "ok");
    } else {
      streak = 0;
      setHint("错误 · 应为「" + byId[currentTrial.inkId].label + "」", "err");
    }
    document.getElementById("streak").textContent = String(streak);
    document.getElementById("correct-n").textContent = String(correct);
    document.getElementById("rt-display").textContent = ok ? ("RT " + rt + " ms") : "";

    if (mode === "challenge") {
      progressEl.textContent = trialLimit > 0 ? (total + " / " + trialLimit) : ("试次 " + total);
      if (trialLimit > 0 && total >= trialLimit) {
        setTimeout(finishChallenge, 700);
        return;
      }
    }
    if (mode === "casual") {
      setTimeout(showTrial, ok ? 400 : 900);
    } else {
      setTimeout(showTrial, 500);
    }
  }

  function updateChrome() {
    var name = diffLabel(diffKey);
    labelEl.textContent = (mode === "casual" ? "休闲" : "挑战") + " · " + name;
    document.getElementById("btn-next").style.display = mode === "casual" ? "" : "none";
    progressEl.textContent = mode === "challenge" && trialLimit > 0 ? ("0 / " + trialLimit) : "";
  }

  function startCasual() {
    ensureDifficulty(function () {
      mode = "casual";
      applyDiff();
      stopTimer();
      resetStats();
      updateChrome();
      document.getElementById("timer-text").textContent = "—";
      showView(views, "play");
      showTrial();
    });
  }

  function startChallenge() {
    ensureDifficulty(function () {
      mode = "challenge";
      applyDiff();
      resetStats();
      startedAt = Date.now();
      if (timeLimitMs > 0) {
        deadline = startedAt + timeLimitMs;
      } else {
        deadline = startedAt + 86400000;
        document.getElementById("timer-text").textContent = "00:00";
      }
      updateChrome();
      showView(views, "play");
      startTimer();
      showTrial();
    });
  }

  function finishChallenge() {
    stopTimer();
    var elapsed = Date.now() - startedAt;
    document.getElementById("st-total").textContent = String(total);
    document.getElementById("st-correct").textContent = String(correct);
    document.getElementById("st-rate").textContent = total ? Math.round((correct / total) * 100) + "%" : "0%";
    document.getElementById("st-time").textContent = fmtTime(elapsed);
    document.getElementById("st-rt").textContent = fmtMs(avg(rts));
    var ac = avg(rtsCong), ai = avg(rtsIncong);
    document.getElementById("st-rt-cong").textContent = fmtMs(ac);
    document.getElementById("st-rt-incong").textContent = fmtMs(ai);
    document.getElementById("st-interference").textContent =
      (ac != null && ai != null) ? (ai - ac) + " ms" : "—";
    document.getElementById("st-streak").textContent = String(maxStreak);
    document.getElementById("result-sub").textContent =
      correct === total && total > 0 ? "全部正确！" : "本局挑战结束";
    showView(views, "result");
    celebrate(correct === total && total > 0 ? "全部正确！" : FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") fgbSubmitScore({
      gameId: "stroop", mode: "challenge", tier: diffKey,
      metrics: { correct: correct, total: total, timeMs: elapsed, maxStreak: maxStreak }
    });
  }

  document.getElementById("btn-casual").addEventListener("click", function () { showView(views, "casual"); });
  document.getElementById("btn-casual-back").addEventListener("click", function () { showView(views, "home"); });
  document.getElementById("btn-casual-start").addEventListener("click", startCasual);
  document.getElementById("btn-challenge").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-setup-back").addEventListener("click", function () { showView(views, "home"); });
  document.getElementById("btn-start").addEventListener("click", startChallenge);
  function bindDiffChoice(selector) {
    document.querySelectorAll(selector).forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(selector).forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        diffKey = btn.dataset.diff;
      });
    });
  }
  bindDiffChoice("#casual-diff button");
  bindDiffChoice("#diff-choices button");
  document.getElementById("btn-exit").addEventListener("click", function () {
    function doExit() {
      stopTimer();
      if (mode === "challenge" && total > 0) finishChallenge();
      else if (mode === "casual" && total > 0 && typeof fgbSubmitScore === "function") {
        fgbSubmitScore({
          gameId: "stroop", mode: "casual", tier: diffKey,
          metrics: { correct: correct, total: total, maxStreak: maxStreak }
        });
        showView(views, "home");
      } else showView(views, "home");
    }
    if (mode === "challenge" && total > 0) {
      askConfirm(FGB_MSG.exitConfirm, doExit);
      return;
    }
    doExit();
  });
  document.getElementById("btn-next").addEventListener("click", showTrial);
  document.getElementById("btn-again").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-home").addEventListener("click", function () { stopTimer(); showView(views, "home"); });

  ensureDifficulty(function () {
    if (window.__FGB_IS_DAILY__ || /(?:^|[?&])daily=1(?:&|$)/.test(location.search || "")) {
      var dq = window.__FGB_DAILY_Q__ || {};
      if (!dq.tier) dq.tier = (new URLSearchParams(location.search || "")).get("tier") || "normal";
      if (dq.tier && DIFF[dq.tier]) { diffKey = dq.tier; applyDiff(); }
      startChallenge();
    } else {
      showView(views, "home");
    }
  });
})();
"""


def build_html() -> str:
    return build_page("Stroop 色字干扰", EXTRA_CSS, inject_lobby_link(BODY), SCRIPT)


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate Stroop training HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
