#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""专注力小游戏共享 HTML 样式与输出工具。"""

from __future__ import annotations

import time
from pathlib import Path

# Main family_game_box lobby (not games/hub.html).
LOBBY_HREF = "/"


def lobby_back_link(extra_style: str = "") -> str:
    style = (' style="%s"' % extra_style) if extra_style else ""
    return '<a class="linkish" href="%s"%s>← 返回大厅</a>' % (LOBBY_HREF, style)


def inject_lobby_link(body_html: str) -> str:
    return body_html.replace("{lobby_back_link()}", lobby_back_link())


STANDARD_TIERS = (
    ("intro", "入门"),
    ("simple", "简单"),
    ("normal", "普通"),
    ("hard", "困难"),
    ("master", "大师"),
    ("god", "大神"),
)


def tier_choice_row(
    element_id: str,
    subtitles: dict[str, str] | None = None,
    default: str = "normal",
) -> str:
    """六级难度选择行（data-diff=intro|simple|…）。"""
    subtitles = subtitles or {}
    buttons = []
    for tier_id, label in STANDARD_TIERS:
        active = ' class="active"' if tier_id == default else ""
        sub = subtitles.get(tier_id, "")
        sub_html = (
            '<br><span style="font-weight:500;font-size:.72rem">' + sub + "</span>"
            if sub
            else ""
        )
        buttons.append(
            '<button type="button" data-diff="%s"%s>%s%s</button>'
            % (tier_id, active, label, sub_html)
        )
    return '<div class="choice-row six" id="%s">\n%s\n</div>' % (
        element_id,
        "\n".join(buttons),
    )

COMMON_CSS = r"""
:root {
  --ink: #1a2421;
  --muted: #5c6b66;
  --line: rgba(26, 36, 33, 0.14);
  --paper: #f3efe6;
  --panel: rgba(255, 252, 246, 0.9);
  --accent: #0f7a5a;
  --accent-deep: #0a5240;
  --warn: #9a4a12;
  --danger: #a33b2d;
  --shadow: 0 16px 40px rgba(26, 36, 33, 0.1);
  --display: Cambria, "Songti SC", "Palatino Linotype", serif;
  --sans: "Segoe UI", "PingFang SC", "Microsoft YaHei UI", sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; }
body {
  font-family: var(--sans);
  color: var(--ink);
  background:
    radial-gradient(1000px 520px at 8% -8%, rgba(15,122,90,.15), transparent 55%),
    radial-gradient(800px 420px at 100% 0%, rgba(154,74,18,.09), transparent 50%),
    linear-gradient(165deg, #efe8d8 0%, var(--paper) 45%, #e7eee9 100%);
}
body::before {
  content: "";
  position: fixed; inset: 0; pointer-events: none; opacity: .32;
  background-image:
    linear-gradient(rgba(26,36,33,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(26,36,33,.03) 1px, transparent 1px);
  background-size: 28px 28px;
}
.wrap { position: relative; width: min(560px, calc(100% - 1.5rem)); margin: 0 auto; padding: 1.6rem 0 3rem; }
.wrap.wide { width: min(720px, calc(100% - 1.5rem)); }
.hidden { display: none !important; }
h1 {
  font-family: var(--display);
  font-size: clamp(2rem, 8vw, 3rem);
  margin: 0 0 .35rem;
  letter-spacing: -.02em;
  line-height: .95;
}
h1 em { font-style: italic; color: var(--accent-deep); }
.sub { margin: 0 0 1.4rem; color: var(--muted); line-height: 1.5; }
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: var(--shadow);
  padding: 1.15rem;
}
.mode-grid { display: grid; gap: .75rem; }
.mode-btn {
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem 1.05rem;
  background: #fffdf8;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: transform .15s ease, border-color .15s ease;
}
.mode-btn:hover { transform: translateY(-1px); border-color: rgba(15,122,90,.35); }
.mode-btn strong { display: block; font-size: 1.15rem; margin-bottom: .25rem; }
.mode-btn span { color: var(--muted); font-size: .92rem; }
.choice-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: .6rem; margin: 1rem 0; }
.choice-row.two { grid-template-columns: repeat(2, 1fr); }
.choice-row.six { grid-template-columns: repeat(3, 1fr); }
@media (min-width: 640px) {
  .choice-row.six { grid-template-columns: repeat(6, 1fr); }
}
.choice-row button {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: .9rem .4rem;
  font: inherit;
  font-weight: 700;
  background: #fffdf8;
  cursor: pointer;
}
.choice-row button.active {
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
  color: #f7fffb;
  border-color: transparent;
}
.primary {
  width: 100%;
  border: 0;
  border-radius: 14px;
  padding: .85rem 1rem;
  font: inherit;
  font-weight: 700;
  color: #f7fffb;
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
  cursor: pointer;
}
.ghost {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: .7rem 1rem;
  font: inherit;
  font-weight: 600;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: .75rem;
  margin-bottom: .9rem;
  color: var(--muted);
  font-size: .92rem;
  flex-wrap: wrap;
}
.topbar strong { color: var(--ink); font-variant-numeric: tabular-nums; }
.hint {
  text-align: center;
  min-height: 1.4em;
  margin: 0 0 .8rem;
  color: var(--muted);
  font-size: .95rem;
}
.hint.err { color: var(--danger); }
.hint.ok { color: var(--accent-deep); font-weight: 600; }
.actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: .55rem;
  margin-top: .75rem;
}
.actions.two { grid-template-columns: repeat(2, 1fr); }
.actions button {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: .7rem .3rem;
  font: inherit;
  font-weight: 600;
  background: #fffdf8;
  cursor: pointer;
  color: var(--ink);
}
.actions button.warn { color: var(--warn); }
.actions button.danger { color: var(--danger); }
.stats-list { margin: .8rem 0 1.1rem; padding: 0; list-style: none; }
.stats-list li {
  display: flex;
  justify-content: space-between;
  padding: .55rem 0;
  border-bottom: 1px dashed var(--line);
}
.stats-list li:last-child { border-bottom: 0; }
.linkish {
  display: inline-block;
  margin-top: 1rem;
  color: var(--accent-deep);
  text-decoration: none;
  font-weight: 600;
}
.grid-cells {
  display: grid;
  gap: 2px;
  margin: .5rem 0;
  user-select: none;
}
.grid-cells button, .grid-cells .cell {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fffdf8;
  font: inherit;
  font-weight: 600;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  min-height: 28px;
}
.grid-cells button.marked {
  background: rgba(15,122,90,.18);
  color: var(--accent-deep);
  text-decoration: line-through;
}
.grid-cells button.found {
  background: rgba(15,122,90,.25);
  box-shadow: inset 0 0 0 2px var(--accent);
}
.grid-cells button.wrong-flash {
  animation: wrongFlash .5s ease;
}
@keyframes wrongFlash {
  0%, 100% { background: #fffdf8; }
  50% { background: rgba(163,59,45,.25); }
}
.task-bar {
  text-align: center;
  padding: .65rem .8rem;
  border-radius: 12px;
  background: rgba(15,122,90,.08);
  color: var(--accent-deep);
  font-weight: 600;
  margin-bottom: .85rem;
}
"""

OVERLAY_CSS = r"""
.confirm-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(26, 36, 33, 0.42);
  backdrop-filter: blur(2px);
}
.confirm-mask.hidden { display: none !important; }
.confirm-box {
  width: min(360px, 100%);
  background: #fffdf8;
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: var(--shadow);
  padding: 1.25rem 1.2rem 1.1rem;
}
.confirm-box p {
  margin: 0 0 1.1rem;
  font-size: 1.05rem;
  line-height: 1.45;
  color: var(--ink);
}
.confirm-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .55rem;
}
.confirm-actions button {
  border-radius: 14px;
  padding: .75rem 1rem;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.confirm-actions .confirm-cancel {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--muted);
}
.confirm-actions .confirm-ok {
  border: 0;
  color: #f7fffb;
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
}
/* 统一完成反馈：轻量、不挡操作 */
.celebrate {
  position: fixed;
  left: 50%;
  top: 18%;
  transform: translate(-50%, -12px) scale(.92);
  z-index: 1100;
  pointer-events: none;
  opacity: 0;
  transition: opacity .18s ease, transform .28s cubic-bezier(.2,.9,.3,1.2);
}
.celebrate.show {
  opacity: 1;
  transform: translate(-50%, 0) scale(1);
}
.celebrate-pill {
  display: flex;
  align-items: center;
  gap: .55rem;
  padding: .7rem 1.1rem .7rem .85rem;
  border-radius: 999px;
  background: rgba(255, 252, 246, 0.96);
  border: 1px solid rgba(15,122,90,.28);
  box-shadow: 0 12px 32px rgba(26,36,33,.14);
  color: var(--accent-deep);
  font-weight: 700;
  font-size: 1rem;
  white-space: nowrap;
}
.celebrate-mark {
  width: 1.55rem;
  height: 1.55rem;
  border-radius: 50%;
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
  color: #f7fffb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .95rem;
  line-height: 1;
  flex-shrink: 0;
  box-shadow: 0 0 0 0 rgba(15,122,90,.35);
  animation: celebratePulse .55s ease;
}
@keyframes celebratePulse {
  0% { box-shadow: 0 0 0 0 rgba(15,122,90,.4); transform: scale(.85); }
  60% { box-shadow: 0 0 0 10px rgba(15,122,90,0); transform: scale(1.06); }
  100% { box-shadow: 0 0 0 0 rgba(15,122,90,0); transform: scale(1); }
}
.celebrate-burst {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 8px;
  height: 8px;
  margin: -4px 0 0 -4px;
  border-radius: 50%;
  background: var(--accent);
  opacity: 0;
}
.celebrate.show .celebrate-burst {
  animation: celebrateBurst .5s ease forwards;
}
.celebrate-burst:nth-child(1) { --dx: -28px; --dy: -22px; }
.celebrate-burst:nth-child(2) { --dx: 30px; --dy: -18px; background: #c9a227; }
.celebrate-burst:nth-child(3) { --dx: -22px; --dy: 24px; background: #9a4a12; }
.celebrate-burst:nth-child(4) { --dx: 26px; --dy: 20px; background: #2471a3; }
.celebrate-burst:nth-child(5) { --dx: 0; --dy: -32px; background: #7d3c98; }
.celebrate-burst:nth-child(6) { --dx: 0; --dy: 30px; background: #1e8449; }
@keyframes celebrateBurst {
  0% { opacity: .9; transform: translate(0,0) scale(1); }
  100% { opacity: 0; transform: translate(var(--dx), var(--dy)) scale(.3); }
}
"""

COMMON_JS_CORE = r"""
function showView(views, name) {
  if (window.__FGB_IS_DAILY__ && name !== "play") return;
  Object.keys(views).forEach(function (k) {
    views[k].classList.toggle("hidden", k !== name);
  });
}
function fmtTime(ms) {
  var s = Math.floor(ms / 1000);
  var m = Math.floor(s / 60);
  var r = s % 60;
  return String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0");
}
function shuffle(arr) {
  var a = arr.slice();
  for (var i = a.length - 1; i > 0; i--) {
    var j = (Math.random() * (i + 1)) | 0;
    var t = a[i]; a[i] = a[j]; a[j] = t;
  }
  return a;
}
function randInt(n) { return (Math.random() * n) | 0; }
function pick(arr) { return arr[randInt(arr.length)]; }
"""

OVERLAY_JS = r"""
var FGB_MSG = {
  exitConfirm: "退出并查看统计？",
  done: "完成！",
  sessionDone: "本局完成！"
};

var _confirmCb = null;
function askConfirm(message, onYes, onNo) {
  var mask = document.getElementById("confirm-mask");
  var msg = document.getElementById("confirm-msg");
  if (!mask || !msg) {
    if (onYes) onYes();
    return;
  }
  msg.textContent = message || FGB_MSG.exitConfirm;
  _confirmCb = { yes: onYes, no: onNo };
  mask.classList.remove("hidden");
}
function _resolveConfirm(ok) {
  var mask = document.getElementById("confirm-mask");
  if (mask) mask.classList.add("hidden");
  var cb = _confirmCb;
  _confirmCb = null;
  if (!cb) return;
  if (ok && cb.yes) cb.yes();
  if (!ok && cb.no) cb.no();
}
(function bindConfirmUI() {
  var ok = document.getElementById("confirm-ok");
  var cancel = document.getElementById("confirm-cancel");
  var mask = document.getElementById("confirm-mask");
  if (ok) ok.addEventListener("click", function () { _resolveConfirm(true); });
  if (cancel) cancel.addEventListener("click", function () { _resolveConfirm(false); });
  if (mask) mask.addEventListener("click", function (e) {
    if (e.target === mask) _resolveConfirm(false);
  });
})();

var _celebrateTimer = null;
/** 轻量完成动效：不挡点击，约 0.5s 自动消失 */
function celebrate(message) {
  var el = document.getElementById("celebrate");
  var text = document.getElementById("celebrate-text");
  if (!el || !text) return;
  text.textContent = message || FGB_MSG.done;
  el.classList.remove("show");
  void el.offsetWidth;
  el.classList.add("show");
  el.classList.remove("hidden");
  if (_celebrateTimer) clearTimeout(_celebrateTimer);
  _celebrateTimer = setTimeout(function () {
    el.classList.remove("show");
    setTimeout(function () { el.classList.add("hidden"); }, 200);
  }, 520);
}
/** 播完成动效后短延迟回调；默认 480ms，几乎不拖慢下一局 */
function celebrateThen(message, callback, delayMs) {
  celebrate(message);
  var wait = delayMs == null ? 480 : delayMs;
  setTimeout(function () {
    if (callback) callback();
  }, wait);
}
"""

COMMON_JS_UTILS = COMMON_JS_CORE + OVERLAY_JS

CONFIRM_HTML = """
<div class="confirm-mask hidden" id="confirm-mask" role="dialog" aria-modal="true">
  <div class="confirm-box">
    <p id="confirm-msg">确定？</p>
    <div class="confirm-actions">
      <button type="button" class="confirm-cancel" id="confirm-cancel">取消</button>
      <button type="button" class="confirm-ok" id="confirm-ok">确定</button>
    </div>
  </div>
</div>
<div class="celebrate hidden" id="celebrate" aria-live="polite">
  <span class="celebrate-burst"></span>
  <span class="celebrate-burst"></span>
  <span class="celebrate-burst"></span>
  <span class="celebrate-burst"></span>
  <span class="celebrate-burst"></span>
  <span class="celebrate-burst"></span>
  <div class="celebrate-pill">
    <span class="celebrate-mark">✓</span>
    <span id="celebrate-text">完成！</span>
  </div>
</div>
"""

DAILY_HEAD = r"""
<script>
(function () {
  if (/(?:^|[?&])daily=1(?:&|$)/.test(location.search || "")) {
    document.documentElement.classList.add("fgb-daily-mode");
  }
})();
</script>
<style>
html.fgb-daily-mode #view-home,
html.fgb-daily-mode #view-setup,
html.fgb-daily-mode #view-casual,
html.fgb-daily-mode #view-size,
html.fgb-daily-mode #view-result,
html.fgb-daily-mode #view-casual-done { display: none !important; }
html.fgb-daily-mode .mode-btn,
html.fgb-daily-mode #casual-extra,
html.fgb-daily-mode #btn-next,
html.fgb-daily-mode #btn-restart { display: none !important; }
</style>
"""

DAILY_BOOT_JS = r"""
(function () {
  var qraw = location.search || "";
  if (!/(?:^|[?&])daily=1(?:&|$)/.test(qraw)) return;
  var params = new URLSearchParams(qraw);
  var q = {
    daily: true,
    runId: params.get("runId") || "",
    tier: params.get("tier") || "normal",
    seed: Number(params.get("seed") || "0") || 1,
    stageIndex: Number(params.get("stageIndex") || "0") || 0,
  };
  window.__FGB_DAILY_Q__ = q;
  window.__FGB_IS_DAILY__ = true;
  document.documentElement.classList.add("fgb-daily-mode");
  if (window.FGBDaily && FGBDaily.installMathRandom) {
    FGBDaily.installMathRandom(q.seed);
  }
  window.fgbSubmitScore = function (payload) {
    var ms = 0;
    if (payload && payload.metrics && payload.metrics.timeMs != null) ms = payload.metrics.timeMs | 0;
    if (window.FGBDaily && FGBDaily.notifyStageDone) FGBDaily.notifyStageDone(ms);
    else if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "fgb-daily-stage-done", timeMs: ms }, "*");
    }
  };
  function abortDaily(e) {
    if (e) {
      e.preventDefault();
      if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      else e.stopPropagation();
    }
    if (window.FGBDaily && FGBDaily.notifyAbort) FGBDaily.notifyAbort();
    else if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "fgb-daily-abort" }, "*");
    }
  }
  document.querySelectorAll('a.linkish[href="/"], a[href="/"]').forEach(function (a) {
    a.textContent = "退出本关";
    a.href = "#";
    a.addEventListener("click", abortDaily);
  });
  // 游戏内退出按钮：每日模式禁止 show(home)，须通知父页结束挑战
  ["btn-exit", "btn-exit-casual", "btn-exit-challenge"].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("click", abortDaily, true);
  });
})();
"""


def inject_standalone_overlays(html: str, *, include_fgb_client: bool = True) -> str:
    """为独立 HTML 页注入统一确认框与完成庆祝组件。"""
    if "fgb-daily-mode #view-home" not in html:
        if "</head>" in html:
            html = html.replace("</head>", DAILY_HEAD + "\n</head>", 1)
        elif "</style>" in html:
            html = html.replace("</style>", "</style>\n" + DAILY_HEAD, 1)
    if ".confirm-mask" not in html:
        html = html.replace("</style>", OVERLAY_CSS + "\n</style>", 1)
    if 'id="confirm-mask"' not in html:
        fgb = '<script src="/js/fgb-client.js"></script>'
        daily_fgb = '<script src="/js/fgb-daily.js"></script>\n' + fgb
        if fgb in html and "/js/fgb-daily.js" not in html:
            html = html.replace(fgb, daily_fgb, 1)
        if daily_fgb in html or fgb in html:
            marker = daily_fgb if daily_fgb in html else fgb
            html = html.replace(
                marker + "\n<script>",
                CONFIRM_HTML + "\n" + marker + "\n<script>",
                1,
            )
        else:
            if include_fgb_client:
                html = html.replace(
                    "<script>",
                    '<script src="/js/fgb-daily.js"></script>\n'
                    '<script src="/js/fgb-client.js"></script>\n<script>',
                    1,
                )
            html = html.replace("</div>\n<script", "</div>\n" + CONFIRM_HTML + "\n<script", 1)
    if "function askConfirm" not in html:
        html = html.replace(
            "<script>\n(function () {",
            "<script>\n" + OVERLAY_JS + "\n(function () {",
            1,
        )
    if "/* fgb-daily-boot */" not in html and "fgb-daily.js" in html:
        html = html.replace(
            '<script src="/js/fgb-client.js"></script>\n<script>',
            '<script src="/js/fgb-client.js"></script>\n<script>\n'
            + "/* fgb-daily-boot */\n"
            + DAILY_BOOT_JS
            + "\n",
            1,
        )
    return html


def build_page(title: str, extra_css: str, body_html: str, script: str, wide: bool = False) -> str:
    wrap_cls = "wrap wide" if wide else "wrap"
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>" + title + "</title>",
        DAILY_HEAD,
        "<style>",
        COMMON_CSS,
        OVERLAY_CSS,
        extra_css,
        "</style>",
        "</head>",
        "<body>",
        '<div class="' + wrap_cls + '">',
        body_html,
        "</div>",
        CONFIRM_HTML,
        '<script src="/js/fgb-daily.js"></script>',
        '<script src="/js/fgb-client.js"></script>',
        "<script>",
        "/* fgb-daily-boot */",
        COMMON_JS_UTILS,
        DAILY_BOOT_JS,
        script,
        "</script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts) + "\n"


def write_outputs(html: str, out: Path, dist: Path, label: str = "") -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    dist.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    dist.write_text(html, encoding="utf-8")
    kb = out.stat().st_size / 1024
    print("Wrote %s (%.1f KB)%s" % (out, kb, (" " + label) if label else ""))
    print("Wrote %s" % dist)


def run_generator(build_fn, out: str, dist: str, label: str) -> None:
    t0 = time.perf_counter()
    html = build_fn()
    write_outputs(html, Path(out), Path(dist), label)
    print("Done in %.2fs" % (time.perf_counter() - t0))
