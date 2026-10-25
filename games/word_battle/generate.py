#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「单词大作战」听音拼写页。"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_GAMES = _HERE.parent
for _p in (_GAMES, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from common.game_common import build_page, inject_lobby_link, run_generator
from common.paths import game_page_paths
from parse_bank import BANK_PATH, main as build_words_json

SLUG = "word-battle"
AUDIO_SRC = Path(__file__).resolve().parent / "audio"

EXTRA_CSS = r"""
.wb-hero { text-align: center; margin-bottom: 1rem; }
.wb-tag {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.35rem;
}
.wb-tier-grid {
  display: grid;
  gap: 0.65rem;
  margin-bottom: 0.85rem;
}
.wb-tier-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.04);
  color: var(--ink);
  font: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
}
.wb-tier-btn strong { font-family: var(--display); font-size: 1.05rem; }
.wb-tier-btn span { font-size: 0.82rem; color: var(--muted); margin-top: 0.2rem; line-height: 1.4; }
.wb-tier-btn:hover, .wb-tier-btn:focus-visible {
  border-color: rgba(251, 191, 36, 0.55);
  outline: none;
  transform: translateY(-1px);
}
.wb-tier-btn.active {
  border-color: rgba(251, 191, 36, 0.7);
  background: rgba(251, 191, 36, 0.1);
}
.wb-console { padding: 1rem 1.05rem; }
.wb-progress {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-size: 0.88rem;
  color: var(--muted);
}
.wb-progress strong { color: var(--ink); font-variant-numeric: tabular-nums; }
.wb-timer {
  font-family: var(--display);
  font-size: 1.2rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--accent);
}
.wb-spell {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.35rem 0.45rem;
  min-height: 3.2rem;
  margin: 0.35rem 0 0.65rem;
  padding: 0.65rem 0.5rem;
  border-radius: 18px;
  border: 1px solid rgba(251, 191, 36, 0.28);
  background: linear-gradient(165deg, rgba(251, 191, 36, 0.1), rgba(12, 20, 17, 0.55));
}
.wb-spell.is-flash-err {
  animation: wbShake 0.35s ease;
  border-color: var(--danger);
}
@keyframes wbShake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}
.wb-char {
  font-family: var(--display);
  font-size: clamp(1.35rem, 5.5vw, 1.85rem);
  font-weight: 700;
  min-width: 1.1em;
  text-align: center;
  letter-spacing: 0.02em;
}
.wb-char.is-punct { color: var(--muted); min-width: auto; }
.wb-char.is-slot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.35em;
  min-height: 1.55em;
  border-radius: 10px;
  border: 2px dashed rgba(255, 255, 255, 0.16);
  color: var(--ink);
  opacity: 0.26;
}
.wb-char.is-slot.is-next {
  opacity: 0.42;
  border-color: rgba(251, 191, 36, 0.55);
  box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.12);
}
.wb-char.is-filled {
  border-style: solid;
  border-color: rgba(62, 207, 142, 0.55);
  background: rgba(62, 207, 142, 0.12);
  color: var(--ink);
  opacity: 1;
}
.wb-char.is-slot.is-speaking {
  opacity: 0.5;
  color: #fde68a;
  border-color: rgba(251, 191, 36, 0.75);
}
.wb-meta {
  text-align: center;
  margin-bottom: 0.65rem;
  line-height: 1.45;
}
.wb-gloss {
  font-size: 1.05rem;
  color: var(--ink);
  margin: 0 0 0.25rem;
}
.wb-ipa {
  font-size: 0.88rem;
  color: var(--muted);
  font-family: var(--display);
}
.wb-kb-toggle {
  display: flex;
  justify-content: center;
  margin-bottom: 0.45rem;
}
.wb-kb-toggle button {
  font-size: 0.82rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.04);
  color: var(--muted);
  cursor: pointer;
}
.wb-kb-toggle button[aria-pressed="true"] {
  border-color: rgba(251, 191, 36, 0.55);
  color: #fde68a;
}
.wb-keyboard {
  display: grid;
  gap: 0.35rem;
  max-width: 420px;
  margin: 0 auto 0.5rem;
}
.wb-keyboard.hidden { display: none; }
.wb-kb-row {
  display: flex;
  justify-content: center;
  gap: 0.28rem;
  flex-wrap: nowrap;
}
.wb-kb-row button {
  flex: 1 1 0;
  min-width: 0;
  max-width: 2.35rem;
  min-height: 44px;
  padding: 0;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.06);
  font-family: var(--display);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ink);
  cursor: pointer;
}
.wb-kb-row button:active { transform: scale(0.96); }
.wb-hint {
  text-align: center;
  min-height: 1.3em;
  font-size: 0.85rem;
  color: var(--muted);
}
.wb-hint.is-wait { color: #fde68a; }
"""

BODY = r"""
  <section id="view-home">
    <div class="wb-hero">
      <p class="wb-tag">听音拼写</p>
      <h1>单词<em>大作战</em></h1>
      <p class="sub">听读音、看释义，按字母拼出英文单词。每局 10 词，错键不计入进度。</p>
    </div>
    <div class="card">
      <p class="hint" style="margin-bottom:.65rem">选择词库难度（按该学段<strong>首现</strong>词表出题）</p>
      <div class="wb-tier-grid" id="tier-pick">
        <button type="button" class="wb-tier-btn active" data-tier="primary">
          <strong>小学</strong>
          <span>课标小学核心词 · 约 576 词可练</span>
        </button>
        <button type="button" class="wb-tier-btn" data-tier="junior">
          <strong>初中</strong>
          <span>初中新增词 · 约 1106 词</span>
        </button>
        <button type="button" class="wb-tier-btn" data-tier="senior">
          <strong>高中</strong>
          <span>高中新增词 · 约 2026 词</span>
        </button>
        <button type="button" class="wb-tier-btn" data-tier="ielts">
          <strong>雅思</strong>
          <span>雅思核心新增 · 约 2936 词</span>
        </button>
      </div>
      <button type="button" class="primary" id="btn-start" style="width:100%">开始挑战</button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-play" class="hidden">
    <div class="card wb-console">
      <div class="wb-progress">
        <span>第 <strong id="wb-q-n">1</strong> / 10 词</span>
        <span class="wb-timer" id="wb-timer" aria-live="polite">0.0s</span>
      </div>
      <div class="wb-spell" id="wb-spell" aria-live="polite"></div>
      <div class="wb-meta">
        <p class="wb-gloss" id="wb-gloss">—</p>
        <p class="wb-ipa" id="wb-ipa"></p>
      </div>
      <div class="wb-kb-toggle">
        <button type="button" id="btn-kb-toggle" aria-pressed="false">显示屏幕键盘</button>
      </div>
      <div class="wb-keyboard hidden" id="wb-keyboard" aria-label="字母键盘"></div>
      <p class="wb-hint" id="wb-hint">正在听读音…</p>
      <button type="button" class="ghost" id="btn-exit" style="width:100%;margin-top:.5rem">退出本局</button>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>本局完成</h1>
    <p class="sub" id="wb-result-sub">10 词拼写完成</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>词库</span><strong id="st-tier">小学</strong></li>
        <li><span>用时</span><strong id="st-time">—</strong></li>
        <li><span>完成词数</span><strong id="st-words">10 / 10</strong></li>
        <li><span>错键次数</span><strong id="st-wrong">0</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>
"""

SCRIPT = r"""
(function () {
  var TOTAL = 10;
  var TIER_LABEL = {
    primary: "小学",
    junior: "初中",
    senior: "高中",
    ielts: "雅思",
  };
  var ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"];
  var LETTER_CLIP_IDS = "abcdefghijklmnopqrstuvwxyz".split("");
  var LETTER_NAMES = {
    a: "ay", b: "bee", c: "see", d: "dee", e: "ee", f: "eff", g: "jee",
    h: "aych", i: "eye", j: "jay", k: "kay", l: "ell", m: "em", n: "en",
    o: "oh", p: "pee", q: "cue", r: "ar", s: "ess", t: "tee", u: "you",
    v: "vee", w: "double you", x: "ex", y: "why", z: "zee",
  };
  var PAUSE_AFTER_LETTER_MS = 260;
  var enVoice = null;
  var letterAudio = FgbAudioClips({
    clipIds: LETTER_CLIP_IDS,
    resolveUrl: function (id) {
      return "audio/" + id + ".mp3";
    },
  });
  letterAudio.warmNetwork();

  var views = {
    home: document.getElementById("view-home"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result"),
  };
  var bank = null;
  var tierKey = "primary";
  var pool = [];
  var round = [];
  var qIndex = 0;
  var letterIdx = 0;
  var wrongKeys = 0;
  var clockStart = 0;
  var timerId = null;
  var accepting = false;
  var introGen = 0;
  var kbVisible = false;
  var rng = Math.random;

  var spellEl = document.getElementById("wb-spell");
  var glossEl = document.getElementById("wb-gloss");
  var ipaEl = document.getElementById("wb-ipa");
  var hintEl = document.getElementById("wb-hint");
  var qnEl = document.getElementById("wb-q-n");
  var timerEl = document.getElementById("wb-timer");
  var kbEl = document.getElementById("wb-keyboard");
  var kbToggle = document.getElementById("btn-kb-toggle");

  function show(name) {
    Object.keys(views).forEach(function (k) {
      views[k].classList.toggle("hidden", k !== name);
    });
  }

  function formatSec(ms) {
    return (ms / 1000).toFixed(1) + "s";
  }

  function elapsedMs() {
    return clockStart ? Date.now() - clockStart : 0;
  }

  function startTimer(anchor) {
    if (timerId) clearInterval(timerId);
    clockStart = anchor || Date.now();
    timerId = setInterval(function () {
      timerEl.textContent = formatSec(elapsedMs());
    }, 200);
    timerEl.textContent = formatSec(0);
  }

  function stopTimer() {
    if (timerId) clearInterval(timerId);
    timerId = null;
  }

  function mulberry32(seed) {
    var t = seed >>> 0;
    return function () {
      t += 0x6d2b79f5;
      var r = Math.imul(t ^ (t >>> 15), 1 | t);
      r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  }

  function letterPositions(word) {
    var out = [];
    var i;
    for (i = 0; i < word.length; i++) {
      if (/[a-zA-Z]/.test(word.charAt(i))) out.push(i);
    }
    return out;
  }

  function pickEnVoice() {
    if (!window.speechSynthesis) return null;
    var voices = speechSynthesis.getVoices() || [];
    var i;
    for (i = 0; i < voices.length; i++) {
      var lang = (voices[i].lang || "").toLowerCase();
      if (lang.indexOf("en-us") >= 0) return voices[i];
    }
    for (i = 0; i < voices.length; i++) {
      var lang2 = (voices[i].lang || "").toLowerCase();
      if (lang2.indexOf("en") === 0) return voices[i];
    }
    return null;
  }

  function ensureVoices() {
    if (enVoice) return;
    enVoice = pickEnVoice();
    if (!enVoice && window.speechSynthesis) {
      speechSynthesis.addEventListener("voiceschanged", function () {
        if (!enVoice) enVoice = pickEnVoice();
      });
    }
  }

  function letterSpeakText(ch) {
    var key = String(ch || "").toLowerCase();
    if (!/^[a-z]$/.test(key)) return "";
    return LETTER_NAMES[key] || key;
  }

  function speakText(text, rate, cancelFirst) {
    if (!text) return Promise.resolve();
    if (!window.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
      return Promise.resolve();
    }
    ensureVoices();
    return new Promise(function (resolve) {
      if (cancelFirst) {
        try {
          window.speechSynthesis.cancel();
        } catch (e) {}
      }
      var u = new SpeechSynthesisUtterance(text);
      u.lang = "en-US";
      u.rate = rate == null ? 0.78 : rate;
      if (enVoice) u.voice = enVoice;
      var done = false;
      function finish() {
        if (done) return;
        done = true;
        resolve();
      }
      u.onend = finish;
      u.onerror = finish;
      window.speechSynthesis.speak(u);
    });
  }

  function playLetterClip(ch) {
    var id = String(ch || "").toLowerCase();
    if (!/^[a-z]$/.test(id)) return Promise.resolve(false);
    letterAudio.unlock();
    return new Promise(function (resolve) {
      letterAudio.play(id, function (ok) {
        resolve(!!ok);
      });
    });
  }

  function playLetterSound(ch) {
    return playLetterClip(ch).then(function (ok) {
      if (ok) return true;
      return speakText(letterSpeakText(ch), 0.78, false).then(function () {
        return false;
      });
    });
  }

  function delay(ms) {
    return new Promise(function (r) { setTimeout(r, ms); });
  }

  function stopSpeech() {
    letterAudio.stop();
    if (!window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
    } catch (e) {}
  }

  function buildKeyboard() {
    kbEl.innerHTML = "";
    ROWS.forEach(function (row) {
      var wrap = document.createElement("div");
      wrap.className = "wb-kb-row";
      for (var i = 0; i < row.length; i++) {
        var ch = row.charAt(i);
        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = ch.toUpperCase();
        btn.dataset.key = ch;
        btn.addEventListener("click", function () {
          handleKey(this.dataset.key);
        });
        wrap.appendChild(btn);
      }
      kbEl.appendChild(wrap);
    });
  }

  function defaultKbVisible() {
    if (window.matchMedia && window.matchMedia("(pointer: coarse)").matches) return true;
    return window.innerWidth < 768;
  }

  function setKbVisible(on) {
    kbVisible = !!on;
    kbEl.classList.toggle("hidden", !kbVisible);
    kbToggle.setAttribute("aria-pressed", kbVisible ? "true" : "false");
    kbToggle.textContent = kbVisible ? "隐藏屏幕键盘" : "显示屏幕键盘";
  }

  function renderSpell(word, filledCount, nextHighlight, speakingIdx) {
    var slots = letterPositions(word);
    spellEl.innerHTML = "";
    spellEl.classList.remove("is-flash-err");
    var i;
    for (i = 0; i < word.length; i++) {
      var span = document.createElement("span");
      var ch = word.charAt(i);
      if (!/[a-zA-Z]/.test(ch)) {
        span.className = "wb-char is-punct";
        span.textContent = ch;
        spellEl.appendChild(span);
        continue;
      }
      var slotNum = slots.indexOf(i);
      span.className = "wb-char is-slot";
      span.textContent = ch;
      if (slotNum < filledCount) {
        span.className = "wb-char is-filled";
      } else if (slotNum === filledCount && nextHighlight) {
        span.classList.add("is-next");
        if (speakingIdx === i) span.classList.add("is-speaking");
      }
      spellEl.appendChild(span);
    }
  }

  function currentWord() {
    return round[qIndex];
  }

  function expectedLetter() {
    var item = currentWord();
    if (!item) return "";
    var slots = letterPositions(item.w);
    if (letterIdx >= slots.length) return "";
    return item.w.charAt(slots[letterIdx]).toLowerCase();
  }

  function flashError() {
    spellEl.classList.add("is-flash-err");
    setTimeout(function () {
      spellEl.classList.remove("is-flash-err");
    }, 360);
  }

  function handleKey(raw) {
    if (!accepting || views.play.classList.contains("hidden")) return;
    var key = String(raw || "").toLowerCase();
    if (!/^[a-z]$/.test(key)) return;
    var want = expectedLetter();
    if (!want) return;
    if (key !== want) {
      wrongKeys += 1;
      flashError();
      return;
    }
    var item = currentWord();
    letterIdx += 1;
    renderSpell(item.w, letterIdx, true, -1);
    playLetterClip(key);
    var slots = letterPositions(item.w);
    if (letterIdx >= slots.length) {
      accepting = false;
      setTimeout(function () { finishWord(); }, 280);
    }
  }

  function finishWord() {
    qIndex += 1;
    if (qIndex >= TOTAL) {
      finishRun();
      return;
    }
    qnEl.textContent = String(qIndex + 1);
    startWord();
  }

  function startWord() {
    var item = currentWord();
    if (!item) return;
    letterIdx = 0;
    accepting = false;
    introGen += 1;
    var myGen = introGen;
    glossEl.textContent = item.gloss || "—";
    var ipa = item.ipa_us || item.ipa_uk || "";
    ipaEl.textContent = ipa ? "/" + ipa + "/" : "";
    renderSpell(item.w, 0, true, -1);
    hintEl.textContent = "正在听读音…";
    hintEl.classList.add("is-wait");
    var slots = letterPositions(item.w);
    var letters = slots.map(function (idx) { return item.w.charAt(idx); });

    (async function () {
      stopSpeech();
      var i;
      for (i = 0; i < letters.length; i++) {
        if (myGen !== introGen) return;
        renderSpell(item.w, 0, true, slots[i]);
        await playLetterSound(letters[i]);
        if (myGen !== introGen) return;
        await delay(PAUSE_AFTER_LETTER_MS);
      }
      if (myGen !== introGen) return;
      renderSpell(item.w, 0, true, -1);
      accepting = true;
      hintEl.textContent = "请拼写单词（键盘或屏幕键）";
      hintEl.classList.remove("is-wait");
      renderSpell(item.w, 0, true, -1);
    })();
  }

  function pickRound() {
    var copy = pool.slice();
    var i;
    for (i = copy.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var tmp = copy[i];
      copy[i] = copy[j];
      copy[j] = tmp;
    }
    round = copy.slice(0, TOTAL);
  }

  function beginPlay() {
    if (!bank || !pool.length) {
      hintEl.textContent = "词库加载失败，请刷新页面";
      return;
    }
    qIndex = 0;
    wrongKeys = 0;
    introGen = 0;
    pickRound();
    show("play");
    qnEl.textContent = "1";
    setKbVisible(defaultKbVisible());
    var run = window.FGBUI && FGBUI.runWhenPlayable
      ? FGBUI.runWhenPlayable.bind(FGBUI)
      : function (prep, done) { prep(); done(Date.now()); };
    letterAudio.unlock();
    run(function () {}, function (t) {
      letterAudio.preloadAll().then(function () {
        startTimer(t);
        startWord();
      });
    });
  }

  function finishRun() {
    stopTimer();
    accepting = false;
    introGen += 1;
    stopSpeech();
    var elapsed = elapsedMs();
    document.getElementById("st-tier").textContent = TIER_LABEL[tierKey] || tierKey;
    document.getElementById("st-time").textContent = formatSec(elapsed);
    document.getElementById("st-words").textContent = TOTAL + " / " + TOTAL;
    document.getElementById("st-wrong").textContent = String(wrongKeys);
    document.getElementById("wb-result-sub").textContent =
      wrongKeys <= 3 ? "拼写很稳！" : "完成 10 词，继续加油！";
    show("result");
    if (typeof celebrate === "function") celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") {
      fgbSubmitScore({
        gameId: "word-battle",
        mode: "challenge",
        tier: tierKey,
        tierLabel: TIER_LABEL[tierKey] || tierKey,
        metrics: {
          timeMs: elapsed,
          correctWords: TOTAL,
          totalWords: TOTAL,
          wrongKeys: wrongKeys,
          correct: TOTAL,
          total: TOTAL,
          done: 1,
        },
      });
    }
  }

  function loadBank() {
    return fetch("words.json", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("words.json");
        return r.json();
      })
      .then(function (data) {
        bank = data;
        rebuildPool();
      });
  }

  function rebuildPool() {
    pool = (bank.words || []).filter(function (w) {
      return w.level === tierKey;
    });
  }

  document.querySelectorAll("#tier-pick .wb-tier-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#tier-pick .wb-tier-btn").forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      tierKey = btn.getAttribute("data-tier") || "primary";
      rebuildPool();
    });
  });

  document.getElementById("btn-start").addEventListener("click", beginPlay);
  document.getElementById("btn-again").addEventListener("click", beginPlay);
  document.getElementById("btn-home").addEventListener("click", function () {
    stopTimer();
    show("home");
  });
  document.getElementById("btn-exit").addEventListener("click", function () {
    if (window.__FGB_IS_DAILY__) return;
    if (typeof askConfirm === "function") {
      askConfirm("确定退出？本局不会记入成绩。", function () {
        stopTimer();
        introGen += 1;
        accepting = false;
        stopSpeech();
        show("home");
      });
    } else {
      stopTimer();
      show("home");
    }
  });
  kbToggle.addEventListener("click", function () {
    setKbVisible(!kbVisible);
  });

  document.addEventListener("keydown", function (e) {
    if (views.play.classList.contains("hidden") || !accepting) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var k = e.key;
    if (k && k.length === 1 && /[a-zA-Z]/.test(k)) {
      e.preventDefault();
      handleKey(k);
    }
  });

  buildKeyboard();
  setKbVisible(defaultKbVisible());
  ensureVoices();

  var seed = Date.now() ^ ((Math.random() * 0x7fffffff) | 0);
  loadBank()
    .then(function () {
      rng = mulberry32(seed);
      show("home");
    })
    .catch(function () {
      show("home");
      var sub = document.querySelector("#view-home .sub");
      if (sub) sub.textContent = "词库加载失败，请稍后刷新。";
    });
})();
"""


def sync_audio(web_index: Path) -> None:
    if not AUDIO_SRC.is_dir():
        print("NOTE: no %s — run games/word_battle/fetch_audio.py" % AUDIO_SRC)
        return
    mp3s = sorted(AUDIO_SRC.glob("*.mp3"))
    if len(mp3s) < 26:
        print("NOTE: expected 26 mp3 in %s (got %d)" % (AUDIO_SRC, len(mp3s)))
        return
    targets = [web_index.parent / "audio"]
    build_index = Path(__file__).resolve().parent / "build" / "index.html"
    targets.append(build_index.parent / "audio")
    readme = AUDIO_SRC / "README.md"
    for dst in targets:
        dst.mkdir(parents=True, exist_ok=True)
        for src in mp3s:
            shutil.copy2(src, dst / src.name)
        if readme.is_file():
            shutil.copy2(readme, dst / "README.md")
        print("Synced %d letter clips → %s" % (len(mp3s), dst))


def build_html() -> str:
    return build_page(
        "单词大作战",
        EXTRA_CSS,
        inject_lobby_link(BODY),
        SCRIPT,
        wide=True,
        game_skin="word-battle",
        game_title="单词大作战",
        audio_clips=True,
    )


def main() -> None:
    if not BANK_PATH.is_file():
        raise SystemExit("missing bank: %s" % BANK_PATH)
    build_words_json()
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate 单词大作战 HTML + words.json.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    run_generator(build_html, args.out, args.dist, SLUG)
    sync_audio(Path(args.dist))


if __name__ == "__main__":
    main()
