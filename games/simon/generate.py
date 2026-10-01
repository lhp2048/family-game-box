#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Simon Says（老师说）训练页 simon.html。"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator, tier_choice_row
from common.paths import game_page_paths

SLUG = "simon"
AUDIO_SRC = Path(__file__).resolve().parent / "audio"

SIMON_TIER_SUB = {
    "intro": "15 试次",
    "simple": "20 试次",
    "normal": "30 试次",
    "hard": "40 试次",
    "master": "50 试次",
    "god": "60 试次",
}

EXTRA_CSS = r"""
.command-box {
  text-align: center;
  font-family: var(--display);
  font-size: clamp(1.4rem, 5vw, 2rem);
  min-height: 3.2em;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  margin: .5rem 0 1rem;
  border-radius: 16px;
  background: rgba(255,255,255,.04);
  border: 1px dashed var(--line);
  line-height: 1.35;
  transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease;
}
.command-box.is-speaking {
  border-color: var(--accent);
  border-style: solid;
  box-shadow: 0 0 0 3px rgba(62,207,142,.22);
  animation: simonSpeakPulse .7s ease-in-out infinite;
}
@keyframes simonSpeakPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}
.tts-note {
  text-align: center;
  font-size: .82rem;
  color: var(--muted);
  min-height: 1.2em;
  margin: -.35rem 0 .55rem;
}
.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: .65rem;
  max-width: 360px;
  margin: 0 auto;
}
.action-grid button {
  border: 1px solid var(--line);
  border-radius: 22px;
  aspect-ratio: 1;
  width: 100%;
  padding: .35rem;
  font: inherit;
  font-weight: 700;
  font-size: clamp(.95rem, 3.2vw, 1.1rem);
  background: rgba(255,255,255,.04);
  color: var(--ink);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  line-height: 1.2;
}
.action-grid button:active { transform: scale(.96); }
.action-grid button:disabled { opacity: .4; cursor: not-allowed; }
.feedback {
  text-align: center;
  min-height: 1.5em;
  margin-top: .75rem;
  font-weight: 600;
}
.toggles { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: .75rem; }
.toggles label {
  display: flex; align-items: center; gap: .35rem;
  font-size: .9rem; color: var(--muted);
}
@media (max-height: 720px), (orientation: landscape) and (max-height: 900px) {
  .command-box {
    min-height: 2.4em;
    padding: .65rem;
    margin: .25rem 0 .55rem;
    font-size: clamp(1.15rem, 3.5vw, 1.55rem);
  }
  .action-grid { max-width: 300px; gap: .5rem; }
  .action-grid button { border-radius: 18px; font-size: .92rem; }
  .feedback { margin-top: .4rem; min-height: 1.2em; }
}
"""

BODY = r"""
  <section id="view-home">
    <h1>Simon<em> Says</em></h1>
    <p class="sub">老师说 · 只有带「老师说」的指令才做动作，否则保持不动。训练听觉专注与冲动控制。</p>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-casual">
        <strong>休闲模式</strong>
        <span>单题练习，可看解析</span>
      </button>
      <button type="button" class="mode-btn" id="btn-challenge">
        <strong>挑战模式</strong>
        <span>20 / 30 / 50 试次，统计冲动错误</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-casual" class="hidden">
    <h1>休闲</h1>
    <p class="sub">选择难度后开始练习。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("casual-diff", SIMON_TIER_SUB) + r"""
      <button type="button" class="primary" id="btn-casual-start">开始</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-casual-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-setup" class="hidden">
    <h1>挑战</h1>
    <p class="sub">选择难度与规则。</p>
    <div class="card">
      <p style="margin:0 0 .5rem;color:var(--muted);font-size:.9rem">难度</p>
      """ + tier_choice_row("diff-choices", SIMON_TIER_SUB) + r"""
      <div class="toggles">
        <label><input type="checkbox" id="chk-tts" checked> 语音朗读</label>
        <label><input type="checkbox" id="chk-reverse"> 反向规则（老师说→不做）</label>
      </div>
      <p style="margin:0 0 .85rem;color:var(--muted);font-size:.82rem">语音用预置 MP3，开着时不显示文字指令（练听力）；关闭则只看文字。播放中也可作答，听不全可能答错。</p>
      <button type="button" class="primary" id="btn-start">开始挑战</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-setup-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-play" class="hidden">
    <div class="topbar">
      <span id="play-label">休闲</span>
      <span id="play-progress">1 / 20</span>
      <span>连击 <strong id="streak">0</strong></span>
    </div>
    <div class="task-bar" id="rule-bar">老师说 → 做动作；无「老师说」→ 不动</div>
    <div class="card">
      <div class="command-box" id="command">准备…</div>
      <div class="tts-note" id="tts-note"></div>
      <div class="action-grid" id="actions">
        <button type="button" data-act="hands_up">↑ 举手</button>
        <button type="button" data-act="turn_left">← 左转</button>
        <button type="button" data-act="jump">跳</button>
        <button type="button" data-act="turn_right">→ 右转</button>
        <button type="button" data-act="squat">蹲</button>
        <button type="button" data-act="hands_down">↓ 放下</button>
      </div>
      <div class="feedback" id="feedback"></div>
      <div class="actions">
        <button type="button" class="danger" id="btn-exit">退出</button>
        <button type="button" id="btn-wait">不动</button>
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
        <li><span>冲动错误</span><strong id="st-impulse">0</strong></li>
        <li><span>有效试次遗漏</span><strong id="st-miss">0</strong></li>
        <li><span>平均反应时</span><strong id="st-rt">—</strong></li>
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
  var ACTIONS = {
    hands_up: "举手",
    hands_down: "放下",
    turn_left: "向左转",
    turn_right: "向右转",
    jump: "跳",
    squat: "蹲"
  };
  var PREFIXES = ["老师说：", "老师说，", "老师说 "];

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
    intro: { label: "入门", trials: 15 },
    simple: { label: "简单", trials: 20 },
    normal: { label: "普通", trials: 30 },
    hard: { label: "困难", trials: 40 },
    master: { label: "大师", trials: 50 },
    god: { label: "大神", trials: 60 }
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
    FGB.loadDifficulty("simon").then(function (cfg) {
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
    trialTotal = d.trials;
  }

  var reverse = false;
  var useTts = true;
  var trialTotal = 30;
  var trialIndex = 0;
  var trial = null;
  var phase = "idle";
  var reactStart = 0;
  var reactTimer = null;
  var presentTimer = null;
  var streak = 0;
  var maxStreak = 0;
  var correct = 0;
  var impulse = 0;
  var miss = 0;
  var rts = [];
  var clipCache = {};
  var activeAudio = null;
  var audioUnlocked = false;
  var commandEl = document.getElementById("command");
  var ttsNoteEl = document.getElementById("tts-note");

  function clipName(trialObj) {
    if (!trialObj) return "";
    return (trialObj.hasPrefix ? "say_" : "") + trialObj.action;
  }

  function clipUrl(name) {
    // 相对当前页：/games/simon/index.html → audio/xxx.mp3（兼容 ROOT_PATH）
    return "audio/" + name + ".mp3";
  }

  function setSpeaking(on) {
    if (!commandEl) return;
    commandEl.classList.toggle("is-speaking", !!on);
  }

  function setTtsNote(msg) {
    if (ttsNoteEl) ttsNoteEl.textContent = msg || "";
  }

  function setCommandHint(msg) {
    if (commandEl) commandEl.textContent = msg || "";
  }

  /** 语音模式默认不露指令文字；失败或关闭语音时再显示 */
  function revealCommandText(trialObj) {
    if (!trialObj) return;
    setCommandHint(trialObj.text);
  }

  function stopSpeak() {
    setSpeaking(false);
    if (activeAudio) {
      try { activeAudio.pause(); } catch (e) {}
      activeAudio = null;
    }
  }

  /** 用户手势下解锁 WebView 音频（Android 内置浏览器常见限制） */
  function unlockAudio() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    try {
      var silent = new Audio(
        "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA"
      );
      silent.volume = 0.01;
      var p = silent.play();
      if (p && p.then) p.catch(function () {});
    } catch (e) {}
  }

  function playClip(name, onDone) {
    if (!name) {
      if (onDone) onDone(false);
      return false;
    }
    var audio = clipCache[name];
    if (!audio) {
      audio = new Audio(clipUrl(name));
      audio.preload = "auto";
      clipCache[name] = audio;
    }
    if (audio.__fgbBad) {
      if (onDone) onDone(false);
      return false;
    }
    try {
      audio.pause();
      audio.currentTime = 0;
    } catch (e) {}
    activeAudio = audio;
    var finished = false;
    function done(ok) {
      if (finished) return;
      finished = true;
      setSpeaking(false);
      activeAudio = null;
      if (!ok) audio.__fgbBad = true;
      if (onDone) onDone(ok);
    }
    audio.onended = function () { done(true); };
    audio.onerror = function () { done(false); };
    setSpeaking(true);
    var playPromise = audio.play();
    if (playPromise && playPromise.then) {
      playPromise.then(function () {
        setTtsNote("");
      }).catch(function () {
        done(false);
      });
    }
    return true;
  }

  /** 统一播预置 MP3；失败则露出文字（不再用 speechSynthesis） */
  function speak(text, trialObj, onDone) {
    if (!useTts) {
      revealCommandText(trialObj);
      if (onDone) onDone(false);
      return;
    }
    stopSpeak();
    setCommandHint("听指令…");
    var name = clipName(trialObj);
    var finished = false;
    function finish(ok) {
      if (finished) return;
      finished = true;
      if (onDone) onDone(ok);
    }
    function visualFallback() {
      revealCommandText(trialObj);
      setTtsNote("语音未加载，请看上方文字");
      setSpeaking(true);
      setTimeout(function () {
        setSpeaking(false);
        finish(false);
      }, 1100);
    }
    if (!name) {
      visualFallback();
      return;
    }
    playClip(name, function (ok) {
      if (ok) {
        setCommandHint("请反应");
        finish(true);
      } else {
        visualFallback();
      }
    });
  }

  function preloadClips() {
    Object.keys(ACTIONS).forEach(function (act) {
      ["", "say_"].forEach(function (prefix) {
        var name = prefix + act;
        if (clipCache[name]) return;
        var a = new Audio(clipUrl(name));
        a.preload = "auto";
        a.addEventListener("error", function () { a.__fgbBad = true; });
        clipCache[name] = a;
      });
    });
  }

  function buildTrial() {
    var keys = Object.keys(ACTIONS);
    var action = keys[randInt(keys.length)];
    var hasPrefix = Math.random() < 0.55;
    var text;
    if (hasPrefix) text = pick(PREFIXES) + ACTIONS[action];
    else text = ACTIONS[action];
    var shouldAct = hasPrefix;
    if (reverse) shouldAct = !shouldAct;
    return { text: text, action: action, hasPrefix: hasPrefix, shouldAct: shouldAct };
  }

  function setActionsEnabled(on) {
    document.querySelectorAll("#actions button").forEach(function (b) {
      b.disabled = !on;
    });
    document.getElementById("btn-wait").disabled = !on;
  }

  function showFeedback(msg, ok) {
    var el = document.getElementById("feedback");
    el.textContent = msg;
    el.style.color = ok ? "var(--accent-deep)" : "var(--danger)";
  }

  function judge(actionTaken) {
    if (phase !== "react") return;
    phase = "done";
    clearTimeout(reactTimer);
    stopSpeak();
    setActionsEnabled(false);
    var rt = Math.round(performance.now() - reactStart);
    var ok = false;
    if (trial.shouldAct) {
      if (actionTaken && actionTaken === trial.action) {
        ok = true;
        rts.push(rt);
      } else if (!actionTaken) {
        miss++;
      }
    } else {
      if (!actionTaken) ok = true;
      else impulse++;
    }
    if (ok) {
      correct++;
      streak++;
      if (streak > maxStreak) maxStreak = streak;
      showFeedback("正确" + (trial.shouldAct && actionTaken ? " · " + rt + " ms" : ""), true);
    } else {
      streak = 0;
      if (trial.shouldAct) showFeedback("错误或遗漏 · 应「" + ACTIONS[trial.action] + "」", false);
      else showFeedback("冲动错误 · 不应动作", false);
    }
    document.getElementById("streak").textContent = String(streak);
    if (mode === "challenge") {
      setTimeout(nextTrial, 900);
    }
  }

  function presentTrial() {
    trial = buildTrial();
    // 开播即可作答：抢答允许，听不全自负
    phase = "react";
    if (useTts) setCommandHint("听指令…");
    else revealCommandText(trial);
    showFeedback("", true);
    setActionsEnabled(true);
    reactStart = performance.now();
    if (presentTimer) clearTimeout(presentTimer);
    clearTimeout(reactTimer);
    speak(trial.text, trial, function () {
      if (phase !== "react") return;
      if (useTts) setCommandHint("请反应");
      // 播完后再给一段时间作答；超时判不动
      reactTimer = setTimeout(function () {
        if (phase === "react") judge(null);
      }, 2800);
    });
  }

  function nextTrial() {
    trialIndex++;
    if (mode === "challenge" && trialIndex >= trialTotal) {
      finishChallenge();
      return;
    }
    document.getElementById("play-progress").textContent =
      (trialIndex + 1) + " / " + (mode === "challenge" ? trialTotal : "∞");
    presentTrial();
  }

  function updateRuleBar() {
    document.getElementById("rule-bar").textContent = reverse
      ? "反向：老师说 → 不做；无「老师说」→ 做"
      : "老师说 → 做动作；无「老师说」→ 不动";
  }

  function startCasual() {
    ensureDifficulty(function () {
      mode = "casual";
      applyDiff();
      reverse = false;
      useTts = true;
      unlockAudio();
      preloadClips();
      trialIndex = 0;
      correct = 0; impulse = 0; miss = 0; streak = 0; maxStreak = 0; rts = [];
      document.getElementById("play-label").textContent = "休闲 · " + diffLabel(diffKey);
      document.getElementById("btn-next").style.display = "";
      setTtsNote("");
      updateRuleBar();
      showView(views, "play");
      nextTrial();
    });
  }

  function startChallenge() {
    ensureDifficulty(function () {
      mode = "challenge";
      applyDiff();
      reverse = document.getElementById("chk-reverse").checked;
      useTts = document.getElementById("chk-tts").checked;
      unlockAudio();
      if (useTts) preloadClips();
      trialIndex = 0;
      correct = 0; impulse = 0; miss = 0; streak = 0; maxStreak = 0; rts = [];
      document.getElementById("play-label").textContent = "挑战 · " + diffLabel(diffKey);
      document.getElementById("btn-next").style.display = "none";
      setTtsNote("");
      updateRuleBar();
      showView(views, "play");
      nextTrial();
    });
  }

  function finishChallenge() {
    clearTimeout(reactTimer);
    if (presentTimer) clearTimeout(presentTimer);
    stopSpeak();
    var total = trialTotal;
    document.getElementById("st-total").textContent = String(total);
    document.getElementById("st-correct").textContent = String(correct);
    document.getElementById("st-rate").textContent = total ? Math.round((correct / total) * 100) + "%" : "0%";
    document.getElementById("st-impulse").textContent = String(impulse);
    document.getElementById("st-miss").textContent = String(miss);
    document.getElementById("st-rt").textContent = rts.length
      ? Math.round(rts.reduce(function (a,b){return a+b;},0)/rts.length) + " ms" : "—";
    document.getElementById("st-streak").textContent = String(maxStreak);
    showView(views, "result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") fgbSubmitScore({
      gameId: "simon", mode: "challenge", tier: diffKey,
      metrics: { correct: correct, total: total, maxStreak: maxStreak, impulse: impulse, miss: miss }
    });
  }

  document.querySelectorAll("#actions button").forEach(function (btn) {
    btn.addEventListener("click", function () { judge(btn.dataset.act); });
  });
  document.getElementById("btn-wait").addEventListener("click", function () { judge(null); });
  document.getElementById("btn-casual").addEventListener("click", function () { showView(views, "casual"); });
  document.getElementById("btn-casual-back").addEventListener("click", function () { showView(views, "home"); });
  document.getElementById("btn-casual-start").addEventListener("click", startCasual);
  document.getElementById("btn-challenge").addEventListener("click", function () { showView(views, "setup"); });
  document.getElementById("btn-setup-back").addEventListener("click", function () { showView(views, "home"); });
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
  document.getElementById("btn-start").addEventListener("click", startChallenge);
  document.getElementById("btn-exit").addEventListener("click", function () {
    function doExit() {
      clearTimeout(reactTimer);
      if (presentTimer) clearTimeout(presentTimer);
      stopSpeak();
      if (mode === "challenge" && trialIndex > 0) finishChallenge();
      else showView(views, "home");
    }
    if (mode === "challenge" && trialIndex > 0) {
      askConfirm(FGB_MSG.exitConfirm, doExit);
      return;
    }
    doExit();
  });
  document.getElementById("btn-next").addEventListener("click", function () {
    if (phase === "react") judge(null);
    else nextTrial();
  });
  document.getElementById("btn-again").addEventListener("click", function () { stopSpeak(); showView(views, "setup"); });
  document.getElementById("btn-home").addEventListener("click", function () { stopSpeak(); showView(views, "home"); });

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


def sync_audio(web_index: Path) -> None:
    """Copy games/simon/audio → web/games/simon/audio (and build twin)."""
    if not AUDIO_SRC.is_dir():
        print("NOTE: no %s yet — run games/simon/gen_audio.py" % AUDIO_SRC)
        return
    targets = [web_index.parent / "audio"]
    build_index = Path(__file__).resolve().parent / "build" / "index.html"
    targets.append(build_index.parent / "audio")
    mp3s = list(AUDIO_SRC.glob("*.mp3"))
    if not mp3s:
        print("NOTE: %s has no .mp3 — run games/simon/gen_audio.py" % AUDIO_SRC)
        return
    for dst in targets:
        dst.mkdir(parents=True, exist_ok=True)
        for src in mp3s:
            shutil.copy2(src, dst / src.name)
        print("Synced %d audio clips → %s" % (len(mp3s), dst))


def build_html() -> str:
    return build_page("Simon Says · 老师说", EXTRA_CSS, inject_lobby_link(BODY), SCRIPT)


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate Simon Says HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)
    sync_audio(Path(args.dist))


if __name__ == "__main__":
    main()
