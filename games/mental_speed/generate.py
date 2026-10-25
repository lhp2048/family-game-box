#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「心算快答」独立小游戏页。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator
from common.paths import game_page_paths

SLUG = "mental-speed"

EXTRA_CSS = r"""
.ms-console { padding: 1rem 1.05rem; }
.ms-hero {
  text-align: center;
  margin-bottom: 1rem;
}
.ms-hero h1 { margin-bottom: 0.35rem; }
.ms-tag {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.35rem;
}
.ms-progress {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.65rem;
  font-size: 0.88rem;
  color: var(--muted);
}
.ms-progress strong { color: var(--ink); font-variant-numeric: tabular-nums; }
.ms-timer {
  font-family: var(--display);
  font-size: 1.35rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--accent);
}
.ms-expr-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 5.5rem;
  margin: 0.5rem 0 0.85rem;
  padding: 1rem 0.75rem;
  border-radius: 20px;
  border: 1px solid rgba(62, 207, 142, 0.28);
  background: linear-gradient(165deg, rgba(62, 207, 142, 0.12), rgba(12, 20, 17, 0.55));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
}
.ms-expr {
  font-family: var(--display);
  font-size: clamp(1.85rem, 7vw, 2.75rem);
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.2;
  text-align: center;
  word-break: break-word;
}
.ms-answer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.ms-answer label {
  font-size: 0.82rem;
  color: var(--muted);
}
.ms-answer-display {
  min-width: 5.5rem;
  min-height: 3rem;
  padding: 0.45rem 0.85rem;
  border-radius: 14px;
  border: 2px solid var(--line);
  background: rgba(0,0,0,0.25);
  font-family: var(--display);
  font-size: 1.85rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: center;
  letter-spacing: 0.08em;
}
.ms-answer-display.is-err {
  border-color: var(--danger);
  animation: msShake 0.35s ease;
}
@keyframes msShake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-6px); }
  75% { transform: translateX(6px); }
}
.ms-numpad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  max-width: 320px;
  margin: 0 auto 0.65rem;
}
.ms-numpad button {
  min-height: 52px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.05);
  font-family: var(--display);
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--ink);
  cursor: pointer;
  transition: transform 0.12s ease, border-color 0.12s ease;
}
.ms-numpad button:active { transform: scale(0.97); }
.ms-numpad button.wide { grid-column: span 2; }
.ms-numpad button.accent {
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
  color: #062016;
  border-color: transparent;
}
.ms-hint {
  text-align: center;
  min-height: 1.35em;
  font-size: 0.88rem;
  color: var(--muted);
  margin-bottom: 0.5rem;
}
.ms-hint.err { color: var(--danger); }
.ms-hint.ok { color: var(--accent); font-weight: 600; }
.ms-countdown {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(4, 10, 8, 0.82);
  backdrop-filter: blur(4px);
}
.ms-countdown.hidden { display: none !important; }
.ms-countdown-num {
  font-family: var(--display);
  font-size: clamp(4rem, 18vw, 7rem);
  font-weight: 700;
  color: var(--accent);
  text-shadow: 0 0 40px rgba(62, 207, 142, 0.45);
}
.ms-penalty {
  font-size: 0.8rem;
  color: var(--warn);
  text-align: center;
  margin-top: -0.25rem;
  margin-bottom: 0.35rem;
  min-height: 1.1em;
}
@media (orientation: landscape) and (min-width: 640px) {
  .wrap { width: min(720px, calc(100% - 1.5rem)); }
  .ms-play-grid {
    display: grid;
    grid-template-columns: 1fr min(300px, 42vw);
    gap: 1rem;
    align-items: start;
  }
}
"""

BODY = r"""
  <section id="view-home">
    <div class="ms-hero">
      <p class="ms-tag">客厅速算</p>
      <h1>心算<em>快答</em></h1>
      <p class="sub">看算式、键入得数。每题 3～4 步运算（4～5 个数），连续 10 题竞速；答错 +3 秒罚时，可重试本题。</p>
    </div>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-start-classic">
        <strong>初阶 · 10 题</strong>
        <span>加减乘除，即时出题，适合热身与亲子对战</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-play" class="hidden">
    <div class="card ms-console">
      <div class="ms-progress">
        <span>第 <strong id="ms-q-n">1</strong> / 10 题</span>
        <span class="ms-timer" id="ms-timer" aria-live="polite">0.0s</span>
      </div>
      <p class="ms-penalty" id="ms-penalty"></p>
      <div class="ms-play-grid">
        <div>
          <div class="ms-expr-wrap">
            <p class="ms-expr" id="ms-expr">—</p>
          </div>
          <p class="ms-hint" id="ms-hint">输入答案后点确认</p>
        </div>
        <div>
          <div class="ms-answer">
            <label for="ms-answer">答案</label>
            <div class="ms-answer-display" id="ms-answer" role="textbox" aria-label="答案" tabindex="0">—</div>
          </div>
          <div class="ms-numpad" id="ms-numpad">
            <button type="button" data-key="1">1</button>
            <button type="button" data-key="2">2</button>
            <button type="button" data-key="3">3</button>
            <button type="button" data-key="4">4</button>
            <button type="button" data-key="5">5</button>
            <button type="button" data-key="6">6</button>
            <button type="button" data-key="7">7</button>
            <button type="button" data-key="8">8</button>
            <button type="button" data-key="9">9</button>
            <button type="button" data-key="clear" class="wide">清除</button>
            <button type="button" data-key="0">0</button>
            <button type="button" data-key="back">⌫</button>
            <button type="button" data-key="submit" class="wide accent">确认</button>
          </div>
        </div>
      </div>
      <button type="button" class="ghost" id="btn-quit" style="width:100%;margin-top:.5rem">退出本局</button>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>结算</h1>
    <p class="sub" id="ms-result-sub">本局结束</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>总用时（含罚时）</span><strong id="st-time">—</strong></li>
        <li><span>答错次数</span><strong id="st-wrong">0</strong></li>
        <li><span>罚时</span><strong id="st-penalty">+0s</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>

  <div class="ms-countdown hidden" id="ms-countdown" aria-hidden="true">
    <span class="ms-countdown-num" id="ms-countdown-num">3</span>
  </div>
"""

SCRIPT = r"""
(function () {
  const TOTAL = 10;
  const PENALTY_MS = 3000;
  const MAX_DIGITS = 3;
  const OPS = ["+", "-", "*", "/"];
  const OP_SYM = { "+": "+", "-": "−", "*": "×", "/": "÷" };

  const views = {
    home: document.getElementById("view-home"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result"),
  };

  function show(name) {
    Object.keys(views).forEach(function (k) {
      views[k].classList.toggle("hidden", k !== name);
    });
  }

  function randInt(lo, hi) {
    return lo + ((Math.random() * (hi - lo + 1)) | 0);
  }

  function pickOp(forceMulDiv) {
    if (forceMulDiv && Math.random() < 0.55) {
      return Math.random() < 0.5 ? "*" : "/";
    }
    return OPS[(Math.random() * OPS.length) | 0];
  }

  function applyOp(a, b, op) {
    if (op === "+") return a + b;
    if (op === "-") return a - b;
    if (op === "*") return a * b;
    if (op === "/") {
      if (b === 0 || a % b !== 0) return null;
      return (a / b) | 0;
    }
    return null;
  }

  function evalLeft(nums, ops) {
    var v = nums[0];
    for (var i = 0; i < ops.length; i++) {
      v = applyOp(v, nums[i + 1], ops[i]);
      if (v === null) return null;
    }
    return v;
  }

  /** 特殊大数乘：积可 >100；连乘中该步之后不能再接 × */
  var MUL_WHITELIST = {
    "4,25": true, "8,25": true,
    "5,20": true, "2,50": true, "4,50": true, "5,25": true,
  };

  function mulPairKey(a, b) {
    var x = a < b ? a : b;
    var y = a < b ? b : a;
    return x + "," + y;
  }

  function isMulWhitelisted(a, b) {
    return !!MUL_WHITELIST[mulPairKey(a, b)];
  }

  /** 单次 × 与连乘中间/最终积：≤100，或白名单大数乘（且白名单后不可再连 ×） */
  function passesMulRules(nums, ops) {
    var v = nums[0];
    for (var i = 0; i < ops.length; i++) {
      var op = ops[i];
      var b = nums[i + 1];
      if (op !== "*") {
        v = applyOp(v, b, op);
        if (v === null) return false;
        continue;
      }
      var prod = v * b;
      if (prod > 100) {
        if (!isMulWhitelisted(v, b)) return false;
        if (i + 1 < ops.length && ops[i + 1] === "*") return false;
        v = prod;
        continue;
      }
      v = prod;
    }
    return true;
  }

  function formatExpr(nums, ops) {
    var parts = [String(nums[0])];
    for (var i = 0; i < ops.length; i++) {
      parts.push(OP_SYM[ops[i]] || ops[i]);
      parts.push(String(nums[i + 1]));
    }
    return parts.join(" ");
  }

  /** 每题 3～4 个运算符（4～5 个操作数） */
  function operatorCountForQuestion() {
    return Math.random() < 0.45 ? 4 : 3;
  }

  function maxOperandForQuestion(qIndex) {
    return qIndex < 5 ? 9 : 12;
  }

  function generateQuestion(qIndex) {
    var opCount = operatorCountForQuestion();
    var n = opCount + 1;
    var maxNum = maxOperandForQuestion(qIndex);
    for (var t = 0; t < 160; t++) {
      var nums = [];
      for (var i = 0; i < n; i++) nums.push(randInt(1, maxNum));
      var ops = [];
      var hasMulDiv = false;
      for (var j = 0; j < opCount; j++) {
        var op = pickOp(j === opCount - 1 && !hasMulDiv);
        ops.push(op);
        if (op === "*" || op === "/") hasMulDiv = true;
      }
      if (!hasMulDiv) continue;
      if (!passesMulRules(nums, ops)) continue;
      var ans = evalLeft(nums, ops);
      if (ans === null || ans < 0 || ans > 999) continue;
      return { text: formatExpr(nums, ops), answer: ans };
    }
    return { text: "2 + 3 × 4 − 1", answer: 13 };
  }

  var tier = "intro";
  var qIndex = 0;
  var wrongCount = 0;
  var penaltyMs = 0;
  var clockStart = 0;
  var timerId = null;
  var current = null;
  var inputStr = "";

  var exprEl = document.getElementById("ms-expr");
  var answerEl = document.getElementById("ms-answer");
  var hintEl = document.getElementById("ms-hint");
  var penaltyEl = document.getElementById("ms-penalty");
  var timerEl = document.getElementById("ms-timer");
  var qnEl = document.getElementById("ms-q-n");
  var countdownEl = document.getElementById("ms-countdown");
  var countdownNum = document.getElementById("ms-countdown-num");

  function formatSec(ms) {
    return (ms / 1000).toFixed(1) + "s";
  }

  function elapsedMs() {
    if (!clockStart) return penaltyMs;
    return Math.max(0, performance.now() - clockStart) + penaltyMs;
  }

  function updateTimer() {
    timerEl.textContent = formatSec(elapsedMs());
  }

  function startClock() {
    clockStart = performance.now();
    stopClock();
    timerId = setInterval(updateTimer, 100);
    updateTimer();
  }

  function stopClock() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  function setInput(str) {
    inputStr = str;
    answerEl.textContent = str.length ? str : "—";
    answerEl.classList.remove("is-err");
  }

  function appendDigit(d) {
    if (inputStr.length >= MAX_DIGITS) return;
    if (inputStr === "0") inputStr = String(d);
    else inputStr += String(d);
    setInput(inputStr);
  }

  function showQuestion() {
    current = generateQuestion(qIndex);
    exprEl.textContent = current.text;
    qnEl.textContent = String(qIndex + 1);
    setInput("");
    hintEl.className = "ms-hint";
    hintEl.textContent = "从左到右计算 · 输入得数";
    penaltyEl.textContent = penaltyMs > 0 ? ("罚时累计 +" + (penaltyMs / 1000).toFixed(0) + "s") : "";
  }

  function runCountdown(done) {
    countdownEl.classList.remove("hidden");
    var left = 3;
    countdownNum.textContent = String(left);
    var tick = setInterval(function () {
      left -= 1;
      if (left <= 0) {
        clearInterval(tick);
        countdownEl.classList.add("hidden");
        done();
        return;
      }
      countdownNum.textContent = String(left);
    }, 700);
  }

  function beginRun() {
    qIndex = 0;
    wrongCount = 0;
    penaltyMs = 0;
    clockStart = 0;
    show("play");
    runCountdown(function () {
      startClock();
      showQuestion();
    });
  }

  function finishRun() {
    stopClock();
    var total = elapsedMs();
    document.getElementById("st-time").textContent = formatSec(total);
    document.getElementById("st-wrong").textContent = String(wrongCount);
    document.getElementById("st-penalty").textContent = "+" + (penaltyMs / 1000).toFixed(0) + "s";
    document.getElementById("ms-result-sub").textContent =
      wrongCount === 0 ? "全部正确，真快！" : "完成 10 题，继续练习会更稳";
    show("result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") {
      fgbSubmitScore({
        gameId: "mental-speed",
        mode: "challenge",
        tier: tier,
        tierLabel: "初阶",
        metrics: {
          timeMs: Math.round(total),
          done: TOTAL,
          correct: TOTAL,
          total: TOTAL,
          wrong: wrongCount,
        },
      });
    }
  }

  function submitAnswer() {
    if (!current || !clockStart) return;
    if (!inputStr.length) {
      hintEl.className = "ms-hint err";
      hintEl.textContent = "请输入答案";
      return;
    }
    var guess = parseInt(inputStr, 10);
    if (!isFinite(guess)) return;
    if (guess === current.answer) {
      hintEl.className = "ms-hint ok";
      hintEl.textContent = "正确！";
      qIndex += 1;
      if (qIndex >= TOTAL) {
        setTimeout(finishRun, 320);
        return;
      }
      setTimeout(function () {
        showQuestion();
      }, 280);
      return;
    }
    wrongCount += 1;
    penaltyMs += PENALTY_MS;
    answerEl.classList.add("is-err");
    hintEl.className = "ms-hint err";
    hintEl.textContent = "不对，+3 秒罚时 · 再试一次";
    penaltyEl.textContent = "罚时累计 +" + (penaltyMs / 1000).toFixed(0) + "s";
    updateTimer();
  }

  function onKey(d) {
    if (d === "clear") setInput("");
    else if (d === "back") setInput(inputStr.slice(0, -1));
    else if (d === "submit") submitAnswer();
    else appendDigit(parseInt(d, 10));
  }

  document.getElementById("ms-numpad").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-key]");
    if (!btn) return;
    onKey(btn.getAttribute("data-key"));
  });

  document.addEventListener("keydown", function (e) {
    if (views.play.classList.contains("hidden")) return;
    if (e.key >= "0" && e.key <= "9") {
      e.preventDefault();
      appendDigit(parseInt(e.key, 10));
      return;
    }
    if (e.key === "Backspace") {
      e.preventDefault();
      onKey("back");
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      submitAnswer();
    }
  });

  document.getElementById("btn-start-classic").addEventListener("click", beginRun);
  document.getElementById("btn-again").addEventListener("click", beginRun);
  document.getElementById("btn-home").addEventListener("click", function () {
    stopClock();
    show("home");
  });
  document.getElementById("btn-quit").addEventListener("click", function () {
    askConfirm("确定退出本局？进度不会保存。", function () {
      stopClock();
      show("home");
    });
  });

  show("home");
})();
"""


def build_html() -> str:
    return build_page(
        "心算快答",
        EXTRA_CSS,
        inject_lobby_link(BODY),
        SCRIPT,
        game_skin="mental-speed",
        game_title="心算快答",
    )


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate 心算快答 HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
