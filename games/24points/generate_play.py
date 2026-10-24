#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 solutions.txt 生成 24 点游玩页 play.html。"""

from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import inject_standalone_overlays
from common.paths import points_page_paths, repo_root
from generate_library import parse_solutions

import math
from typing import Dict, List, Sequence, Tuple

TIER_ORDER = ("intro", "simple", "normal", "hard", "master", "god")
TIER_CUTS = (0.12, 0.28, 0.50, 0.72, 0.88, 1.01)  # cumulative upper fractions
TIER_LABELS = {
    "intro": "入门",
    "simple": "简单",
    "normal": "普通",
    "hard": "困难",
    "master": "大师",
    "god": "大神",
}
TIER_DESCS = {
    "intro": (
        "数字范围：多为 1–9 的小数。\n"
        "是否重复：常出现重复数字。\n"
        "解法难度：解法很多，步骤少，适合刚接触 24 点。"
    ),
    "simple": (
        "数字范围：仍以较小数字为主，偶有稍大一点的数。\n"
        "是否重复：可有重复，也可互异。\n"
        "解法难度：解法较多，步骤不长，偶尔要用乘除。"
    ),
    "normal": (
        "数字范围：小到中等数字都有，较为均衡（推荐）。\n"
        "是否重复：重复与互异都会出现。\n"
        "解法难度：解法数量适中，需要想一想，但不刁钻。"
    ),
    "hard": (
        "数字范围：更容易抽到较大数字（如超过 9）。\n"
        "是否重复：互异数字更多见。\n"
        "解法难度：解法变少，常要括号或整除，需要多想几步。"
    ),
    "master": (
        "数字范围：大数更常见（可到十几）。\n"
        "是否重复：多为四数互异。\n"
        "解法难度：解法少，技巧要求高，适合有经验的玩家。"
    ),
    "god": (
        "数字范围：全库跨度，大数、偏门组合都可能出现。\n"
        "是否重复：以互异为主，极少靠重复套路。\n"
        "解法难度：解极少、结构刁钻，全库最难一档。"
    ),
}


def _expr_ops_div_depth(expr: str) -> Tuple[int, int, int]:
    ops = 0
    has_div = 0
    depth = 0
    max_depth = 0
    for ch in expr:
        if ch in "+-*/":
            ops += 1
            if ch == "/":
                has_div = 1
        elif ch == "(":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        elif ch == ")":
            depth = max(0, depth - 1)
    return ops, has_div, max_depth


def _pick_ref_expr(exprs: Sequence[str]) -> str:
    if not exprs:
        return ""
    return min(exprs, key=lambda e: (len(e), e))


def compute_hardness(nums: Sequence[int], exprs: Sequence[str]) -> float:
    n_sol = max(len(exprs), 1)
    ref = _pick_ref_expr(exprs)
    ops, has_div, depth = _expr_ops_div_depth(ref)
    trivial = 1.0 if (0 in nums or 1 in nums or 24 in nums) else 0.0
    mx = max(nums) if nums else 0
    if mx <= 9:
        range_bonus = 0.0
    elif mx <= 13:
        range_bonus = 0.8
    else:
        range_bonus = 1.6
    dup_bonus = -0.6 if len(set(nums)) < 4 else 0.6
    return (
        3.0 * (1.0 / math.log2(n_sol + 1))
        + 1.0 * ops
        + 1.5 * has_div
        + 0.5 * depth
        - 2.0 * trivial
        + range_bonus
        + dup_bonus
    )


def assign_tiers(scored: List[Tuple[float, Dict]]) -> List[Dict]:
    """scored: list of (hardness, puzzle_dict without t). Mutates and returns puzzles with t."""
    if not scored:
        return []
    scored.sort(key=lambda x: x[0])
    n = len(scored)
    out: List[Dict] = []
    counts = {k: 0 for k in TIER_ORDER}
    for i, (_h, puzzle) in enumerate(scored):
        frac = (i + 1) / float(n)
        tier = TIER_ORDER[-1]
        for name, cut in zip(TIER_ORDER, TIER_CUTS):
            if frac <= cut:
                tier = name
                break
        item = dict(puzzle)
        item["t"] = tier
        counts[tier] += 1
        out.append(item)
    for name in TIER_ORDER:
        if counts[name] < 30:
            print("WARN: tier %s (%s) has only %d puzzles" % (name, TIER_LABELS[name], counts[name]))
    print(
        "Tiers: "
        + ", ".join("%s=%d" % (TIER_LABELS[k], counts[k]) for k in TIER_ORDER)
    )
    return out


def build_play_html() -> str:
    return inject_standalone_overlays(
        _PLAY_HTML,
        game_skin="24points",
        game_title="24 点挑战",
    )



_PLAY_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>24 点挑战</title>
<link rel="stylesheet" href="/css/fgb-theme.css">
<style>
:root {
  --ink: #e8f2ec;
  --muted: #8fa399;
  --line: rgba(232, 242, 236, 0.12);
  --paper: #0c1411;
  --panel: rgba(18, 32, 28, 0.88);
  --accent: #3ecf8e;
  --accent-deep: #1a9f68;
  --warn: #e8a04a;
  --danger: #e07060;
  --shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
  --display: "Fraunces", "Songti SC", "Palatino Linotype", serif;
  --sans: "DM Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; }
body {
  font-family: var(--sans);
  color: var(--ink);
  background:
    radial-gradient(900px 480px at 12% -8%, rgba(62, 207, 142, 0.14), transparent 55%),
    radial-gradient(700px 400px at 100% 0%, rgba(232, 160, 74, 0.06), transparent 50%),
    linear-gradient(165deg, #0a1210 0%, #0c1411 45%, #101a16 100%);
}
body::before {
  content: "";
  position: fixed; inset: 0; pointer-events: none; opacity: .2;
  background-image:
    linear-gradient(rgba(232,242,236,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(232,242,236,.03) 1px, transparent 1px);
  background-size: 28px 28px;
}
.wrap { position: relative; z-index: 1; width: min(560px, calc(100% - 1.5rem)); margin: 0 auto; padding: 1.6rem 0 3rem; }
.hidden { display: none !important; }
@media (max-height: 720px), (orientation: landscape) and (max-height: 900px) {
  .wrap { padding: .55rem 0 1rem; width: min(560px, calc(100% - 1rem)); }
  h1 { font-size: clamp(1.45rem, 4.5vw, 2.1rem); }
  .sub { margin: 0 0 .65rem; font-size: .88rem; }
  .card { padding: .75rem; border-radius: 14px; }
  .topbar { margin-bottom: .45rem; }
  .hint { margin: 0 0 .4rem; min-height: 1.1em; }
  .card-board-wrap { margin: .15rem 0 .35rem; }
  .num-card { min-height: 72px; }
  .num-card .val { font-size: clamp(1.35rem, 5vw, 1.85rem); }
  .ops { gap: .3rem; margin-bottom: .3rem; }
  .ops button { min-height: 44px; padding: .35rem 0; font-size: 1rem; }
  .actions { margin-top: .3rem; gap: .35rem; }
  .actions button { padding: .35rem .2rem; font-size: .82rem; border-radius: 10px; }
  .expr-board { margin: 0 0 .5rem; padding: .5rem .65rem; min-height: 2em; font-size: .85rem; }
  .tip { margin: 0 0 .45rem; padding: .4rem .55rem; font-size: .78rem; }
}
h1 {
  font-family: var(--display);
  font-size: clamp(2.4rem, 9vw, 3.4rem);
  margin: 0 0 .35rem;
  letter-spacing: -.02em;
  line-height: .95;
}
h1 em { font-style: italic; color: var(--accent); }
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
  background: rgba(255,255,255,.04);
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: transform .15s ease, border-color .15s ease;
}
.mode-btn:hover { transform: translateY(-1px); border-color: rgba(62,207,142,.4); }
.mode-btn strong { display: block; font-size: 1.15rem; margin-bottom: .25rem; }
.mode-btn span { color: var(--muted); font-size: .92rem; }
.choice-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: .6rem; margin: 1rem 0; }
.choice-row.tier-row { margin: .75rem 0 .5rem; }
.choice-row button {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: .9rem .4rem;
  font: inherit;
  font-weight: 700;
  background: rgba(255,255,255,.04);
  cursor: pointer;
}
.choice-row.tier-row button { padding: .75rem .35rem; font-size: .95rem; }
.choice-row button.active {
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
  color: #062016;
  border-color: transparent;
}
.setup-label {
  margin: 0;
  font-size: .88rem;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: .04em;
}
.diff-desc {
  margin: 0 0 1rem;
  padding: .75rem .85rem;
  border-radius: 12px;
  background: rgba(62, 207, 142, 0.08);
  color: var(--ink);
  font-size: .92rem;
  line-height: 1.55;
  min-height: 4.5em;
  white-space: pre-line;
}
.primary {
  width: 100%;
  border: 0;
  border-radius: 14px;
  padding: .85rem 1rem;
  font: inherit;
  font-weight: 700;
  color: #062016;
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
.hint.ok { color: var(--accent); font-weight: 600; }

.play-console { padding: 1rem 1.05rem; }
.play-stage {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.card-board-wrap {
  display: flex;
  justify-content: center;
  margin: .25rem 0 .5rem;
  width: 100%;
}
.card-board {
  display: grid;
  gap: .65rem;
  width: min(100%, 420px);
  margin: 0 auto;
  justify-items: stretch;
  align-items: stretch;
}
.card-board[data-count="4"] {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.card-board[data-count="3"] {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  max-width: 340px;
}
.card-board[data-count="3"] .num-card:last-child {
  grid-column: 1 / -1;
  max-width: 52%;
  margin: 0 auto;
  width: 100%;
}
.card-board[data-count="2"] {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  max-width: 340px;
}
.card-board[data-count="1"] {
  grid-template-columns: 1fr;
  max-width: 200px;
}

.num-card {
  position: relative;
  min-height: 5.5rem;
  border: 2px solid rgba(232, 242, 236, 0.14);
  border-radius: 22px;
  background:
    radial-gradient(circle at 28% 22%, rgba(62, 207, 142, 0.14), transparent 50%),
    linear-gradient(165deg, rgba(255,255,255,.07), rgba(12, 20, 17, 0.55));
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.28);
  font-family: var(--display);
  color: var(--ink);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  padding: 0.65rem 0.5rem;
  transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.num-card .val {
  line-height: 1;
  font-size: clamp(1.85rem, 7.5vw, 2.55rem);
  font-variant-numeric: tabular-nums;
}
.num-card .expr {
  font-family: var(--sans);
  font-size: clamp(0.62rem, 2.8vw, 0.78rem);
  font-weight: 600;
  color: var(--muted);
  max-width: 94%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.2;
}
.num-card .kbd-hint {
  position: absolute;
  top: 8px;
  left: 10px;
  font-family: var(--sans);
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--muted);
  opacity: 0.75;
  letter-spacing: 0.02em;
}
.num-card:hover { transform: translateY(-3px); }
.num-card.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(62,207,142,.28), 0 18px 40px rgba(0,0,0,.35);
  transform: translateY(-4px) scale(1.02);
}
.num-card.pulse { animation: cardPulse .45s ease; }
@keyframes cardPulse {
  0% { transform: scale(1); }
  40% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

@media (orientation: landscape) and (min-width: 640px) {
  .wrap { width: min(920px, calc(100% - 1.5rem)); }
  .play-stage {
    display: grid;
    grid-template-columns: 1fr min(300px, 36vw);
    gap: 1.1rem;
    align-items: start;
  }
  .play-controls { position: sticky; top: 0.5rem; }
}

.ops {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: .55rem;
  margin-bottom: .75rem;
}
.ops button {
  border: 1px solid rgba(232, 242, 236, 0.28);
  border-radius: 16px;
  min-height: 48px;
  padding: .85rem 0;
  font-family: var(--display);
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1;
  color: var(--ink);
  background: rgba(232, 242, 236, 0.1);
  cursor: pointer;
  transition: border-color .12s ease, background .12s ease, color .12s ease, transform .12s ease;
}
.ops button:hover {
  border-color: rgba(62, 207, 142, 0.55);
  background: rgba(62, 207, 142, 0.14);
  color: var(--accent);
}
.ops button.active {
  background: rgba(62, 207, 142, 0.22);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 0 2px rgba(62, 207, 142, 0.2);
}
.ops button:disabled { opacity: .4; cursor: not-allowed; }

.actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: .55rem;
  margin-bottom: .65rem;
}
.actions button {
  border: 1px solid var(--line);
  border-radius: 14px;
  min-height: 48px;
  padding: .7rem .3rem;
  font: inherit;
  font-weight: 600;
  background: rgba(255,255,255,.04);
  cursor: pointer;
  color: var(--ink);
}
.frac-toggle {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0 0 0.65rem;
  font-size: 0.82rem;
  color: var(--muted);
  cursor: pointer;
  user-select: none;
}
.frac-toggle input { width: 1.1rem; height: 1.1rem; }
.expr-details {
  margin: 0 0 0.75rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(0,0,0,.15);
}
.expr-details summary {
  padding: 0.5rem 0.75rem;
  font-size: 0.82rem;
  color: var(--muted);
  cursor: pointer;
}
.expr-details .expr-board {
  margin: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}
.actions button.warn { color: var(--warn); }
.actions button.danger { color: var(--danger); }

.extra {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .55rem;
}
.ref {
  margin-top: .8rem;
  padding: .75rem .9rem;
  border-radius: 12px;
  background: rgba(62,207,142,.08);
  font-family: Consolas, monospace;
  font-size: .9rem;
  word-break: break-all;
}
.expr-board {
  margin: 0 0 .85rem;
  padding: .7rem .85rem;
  border-radius: 12px;
  border: 1px solid rgba(62, 207, 142, 0.28);
  background: rgba(18, 32, 28, 0.92);
  font-family: Consolas, "Sarasa Mono SC", monospace;
  font-size: .92rem;
  color: var(--ink);
  min-height: 2.4em;
  line-height: 1.45;
  word-break: break-all;
}
.expr-board strong { color: var(--accent); font-weight: 700; }
.tip {
  margin: 0 0 .75rem;
  padding: .55rem .7rem;
  border-radius: 10px;
  background: rgba(62,207,142,.07);
  color: var(--accent);
  font-size: .82rem;
  line-height: 1.45;
}
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
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
}
.home-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem 1.25rem;
  margin-top: 0.25rem;
}
.home-links .linkish { margin-top: 1rem; }
</style>
</head>
<body>
<div class="wrap">

  <!-- HOME -->
  <section id="view-home">
    <h1>24<em>点</em></h1>
    <p class="sub">选两个数与一个运算合并成新数。可先分别算两组（如 13+23 与 3×4），再把两个结果合并，等价于 ((13+23)-(3×4))。</p>
    <div class="card mode-grid">
      <button type="button" class="mode-btn" id="btn-casual">
        <strong>休闲模式</strong>
        <span>随机出题，可看参考解，不限时</span>
      </button>
      <button type="button" class="mode-btn" id="btn-challenge">
        <strong>挑战模式</strong>
        <span>自选题量，计时作答，结束后统计</span>
      </button>
    </div>
    <p class="home-links">
      <a class="linkish" href="/">← 返回大厅</a>
      <a class="linkish" href="library.html">查看解法库 →</a>
    </p>
  </section>

  <!-- SETUP (casual + challenge) -->
  <section id="view-setup" class="hidden">
    <h1 id="setup-title">开始</h1>
    <p class="sub" id="setup-sub">选择难度后开始。</p>
    <div class="card">
      <p class="setup-label">难度</p>
      <div class="choice-row tier-row" id="tier-choices">
        <button type="button" data-tier="intro">入门</button>
        <button type="button" data-tier="simple">简单</button>
        <button type="button" data-tier="normal" class="active">普通</button>
        <button type="button" data-tier="hard">困难</button>
        <button type="button" data-tier="master">大师</button>
        <button type="button" data-tier="god">大神</button>
      </div>
      <p class="diff-desc" id="diff-desc">数字范围：小到中等数字都有，较为均衡（推荐）。
是否重复：重复与互异都会出现。
解法难度：解法数量适中，需要想一想，但不刁钻。</p>
      <div id="count-block">
        <p class="setup-label">题量</p>
        <div class="choice-row" id="count-choices">
          <button type="button" data-n="5">5 题</button>
          <button type="button" data-n="10" class="active">10 题</button>
          <button type="button" data-n="20">20 题</button>
        </div>
      </div>
      <button type="button" class="primary" id="btn-start">开始</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-setup-back" style="width:100%">返回</button>
    </div>
  </section>

  <!-- PLAY -->
  <section id="view-play" class="hidden">
    <div class="topbar">
      <span id="play-mode-label">休闲</span>
      <span id="play-progress"></span>
      <span id="play-timer" class="hidden"><strong id="timer-text">00:00</strong></span>
    </div>
    <p class="hint" id="play-hint">点选一个数字</p>
    <div class="card play-console">
      <p class="tip">点数字 → 选运算 → 再点数字合并。桌面：<kbd>1</kbd>–<kbd>4</kbd> 选牌，<kbd>+−*/</kbd> 运算，<kbd>Z</kbd> 撤销，<kbd>R</kbd> 重来，<kbd>Esc</kbd> 取消选中。</p>
      <div class="play-stage">
        <div class="card-board-wrap">
          <div class="card-board" id="card-board" data-count="4" role="group" aria-label="数字牌"></div>
        </div>
        <div class="play-controls">
          <label class="frac-toggle" id="frac-toggle-wrap">
            <input type="checkbox" id="chk-fraction">
            <span>允许分数中间值（整除仍推荐）</span>
          </label>
          <div class="ops" id="ops">
            <button type="button" data-op="+">+</button>
            <button type="button" data-op="-">−</button>
            <button type="button" data-op="*">×</button>
            <button type="button" data-op="/">÷</button>
          </div>
          <div class="actions">
            <button type="button" class="danger" id="btn-exit">退出</button>
            <button type="button" class="warn" id="btn-restart">重来</button>
            <button type="button" id="btn-undo">上一步</button>
          </div>
          <div class="extra" id="casual-extra">
            <button type="button" class="ghost" id="btn-hint">看参考解</button>
            <button type="button" class="ghost" id="btn-next">下一题</button>
          </div>
        </div>
      </div>
      <details class="expr-details">
        <summary>展开当前式子</summary>
        <div class="expr-board" id="expr-board">—</div>
      </details>
      <div class="ref hidden" id="ref-box"></div>
    </div>
  </section>

  <!-- RESULT -->
  <section id="view-result" class="hidden">
    <h1>结算</h1>
    <p class="sub" id="result-sub">本局挑战结束</p>
    <div class="card">
      <ul class="stats-list">
        <li><span>题量</span><strong id="st-total">0</strong></li>
        <li><span>完成</span><strong id="st-done">0</strong></li>
        <li><span>用时</span><strong id="st-time">00:00</strong></li>
        <li><span>完成率</span><strong id="st-rate">0%</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-home" style="width:100%">回首页</button>
    </div>
  </section>

</div>

<script>
(function () {
  const TARGET = 24;
  const homeView = document.getElementById("view-home");

  function showFatal(msg) {
    document.body.innerHTML =
      '<div style="max-width:480px;margin:48px auto;padding:24px;font-family:sans-serif">' +
      "<h1>24 点挑战</h1>" +
      "<p style='color:#a33b2d'>" + msg + "</p>" +
      '<p><a href="/" style="color:#0a5240">返回大厅</a></p></div>';
  }

  function boot(BANK) {
  const views = {
    home: document.getElementById("view-home"),
    setup: document.getElementById("view-setup"),
    play: document.getElementById("view-play"),
    result: document.getElementById("view-result"),
  };

  function show(name) {
    if (window.__FGB_IS_DAILY__ && name !== "play") return;
    Object.keys(views).forEach(k => views[k].classList.toggle("hidden", k !== name));
  }

  function fmtTime(ms) {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0");
  }

  let allowFractionMiddle = false;

  function formatValue(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    if (Math.abs(v - Math.round(v)) < 1e-9) return String(Math.round(v));
    var rounded = Math.round(v * 1000) / 1000;
    return String(rounded);
  }

  function isTargetValue(v) {
    return Math.abs(v - TARGET) < 1e-6;
  }

  function applyOp(a, b, op) {
    if (op === "+") return a + b;
    if (op === "-") return a - b;
    if (op === "*") return a * b;
    if (op === "/") {
      if (b === 0) return null;
      if (allowFractionMiddle) {
        var q = a / b;
        return isFinite(q) ? q : null;
      }
      if (a % b !== 0) return null;
      return (a / b) | 0;
    }
    return null;
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = (Math.random() * (i + 1)) | 0;
      const t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  const TIER_ORDER = ["intro", "simple", "normal", "hard", "master", "god"];
  const TIER_DESCS = {
    intro: "数字范围：多为 1–9 的小数。\n是否重复：常出现重复数字。\n解法难度：解法很多，步骤少，适合刚接触 24 点。",
    simple: "数字范围：仍以较小数字为主，偶有稍大一点的数。\n是否重复：可有重复，也可互异。\n解法难度：解法较多，步骤不长，偶尔要用乘除。",
    normal: "数字范围：小到中等数字都有，较为均衡（推荐）。\n是否重复：重复与互异都会出现。\n解法难度：解法数量适中，需要想一想，但不刁钻。",
    hard: "数字范围：更容易抽到较大数字（如超过 9）。\n是否重复：互异数字更多见。\n解法难度：解法变少，常要括号或整除，需要多想几步。",
    master: "数字范围：大数更常见（可到十几）。\n是否重复：多为四数互异。\n解法难度：解法少，技巧要求高，适合有经验的玩家。",
    god: "数字范围：全库跨度，大数、偏门组合都可能出现。\n是否重复：以互异为主，极少靠重复套路。\n解法难度：解极少、结构刁钻，全库最难一档。",
  };
  const TIER_LABELS = {
    intro: "入门", simple: "简单", normal: "普通",
    hard: "困难", master: "大师", god: "大神",
  };
  let tierCuts = [0.12, 0.28, 0.50, 0.72, 0.88, 1.01];
  const DEFAULT_RANGES = {
    intro: { minNum: 1, maxNum: 9 },
    simple: { minNum: 1, maxNum: 10 },
    normal: { minNum: 1, maxNum: 12 },
    hard: { minNum: 1, maxNum: 13 },
    master: { minNum: 1, maxNum: 16 },
    god: { minNum: 1, maxNum: 24 },
  };
  let tierRanges = {};
  TIER_ORDER.forEach(function (tid) {
    tierRanges[tid] = Object.assign({}, DEFAULT_RANGES[tid] || { minNum: 1, maxNum: 24 });
  });
  let rankedBank = BANK.slice();

  function mergeDifficultyConfig(cfg) {
    if (!cfg) return;
    if (Array.isArray(cfg.cuts) && cfg.cuts.length === 6) tierCuts = cfg.cuts.slice();
    if (cfg.tiers) {
      Object.keys(cfg.tiers).forEach(function (k) {
        var t = cfg.tiers[k];
        if (!t) return;
        if (t.label) TIER_LABELS[k] = t.label;
        if (t.desc) TIER_DESCS[k] = t.desc;
        var mn = t.minNum != null ? Number(t.minNum) : 1;
        var mx = t.maxNum != null ? Number(t.maxNum) : 24;
        tierRanges[k] = { minNum: mn, maxNum: mx };
      });
    }
  }

  function assignTierByCuts(puzzles, cuts) {
    var n = puzzles.length;
    return puzzles.map(function (p, i) {
      var frac = (i + 1) / n;
      var tier = "god";
      for (var c = 0; c < cuts.length; c++) {
        if (frac <= cuts[c]) { tier = TIER_ORDER[c]; break; }
      }
      return Object.assign({}, p, { t: tier });
    });
  }

  function inNumRange(p, minN, maxN) {
    return (p.n || []).every(function (x) { return x >= minN && x <= maxN; });
  }

  function rebuildRankedBank() {
    var sorted = BANK.slice().sort(function (a, b) { return (a.h || 0) - (b.h || 0); });
    rankedBank = assignTierByCuts(sorted, tierCuts);
  }

  function ensureDifficulty(thenFn) {
    if (!window.FGB || !FGB.loadDifficulty) {
      rebuildRankedBank();
      thenFn();
      return;
    }
    FGB.loadDifficulty("24points").then(function (cfg) {
      mergeDifficultyConfig(cfg);
      rebuildRankedBank();
      thenFn();
    });
  }

  let mode = "casual"; // casual | challenge
  let selectedTier = "normal";
  let challengeCount = 10;
  let challengeTotal = 0;
  let remaining = [];
  let done = 0;
  let startedAt = 0;
  let casualStartedAt = 0;
  let timerId = null;

  let tiles = []; // {id, value, expr}
  let nextId = 1;
  let history = [];
  let pickA = null;
  let pickOp = null;
  let currentPuzzle = null;
  let solved = false;

  const cardBoard = document.getElementById("card-board");
  const hintEl = document.getElementById("play-hint");
  const refBox = document.getElementById("ref-box");
  const opsEl = document.getElementById("ops");
  const exprBoard = document.getElementById("expr-board");
  const diffDesc = document.getElementById("diff-desc");
  const countBlock = document.getElementById("count-block");

  function setHint(text, cls) {
    hintEl.textContent = text;
    hintEl.className = "hint" + (cls ? " " + cls : "");
  }

  function updateDiffDesc() {
    diffDesc.textContent = TIER_DESCS[selectedTier] || "";
  }

  function openSetup(nextMode) {
    mode = nextMode;
    document.getElementById("setup-title").textContent =
      nextMode === "challenge" ? "挑战" : "休闲";
    document.getElementById("setup-sub").textContent =
      nextMode === "challenge"
        ? "选择难度与题量，开始后计时。"
        : "选择难度后开始，可看参考解，不限时。";
    countBlock.classList.toggle("hidden", nextMode !== "challenge");
    updateDiffDesc();
    show("setup");
  }

  function poolForTier(tierIds, minN, maxN) {
    const set = {};
    tierIds.forEach(t => { set[t] = true; });
    return rankedBank.filter(function (p) {
      var tid = p.t || "normal";
      if (!set[tid]) return false;
      return inNumRange(p, minN, maxN);
    });
  }

  function adjacentTier(tier) {
    const idx = TIER_ORDER.indexOf(tier);
    const normalIdx = TIER_ORDER.indexOf("normal");
    const order = [];
    for (let d = 1; d < TIER_ORDER.length; d++) {
      if (idx - d >= 0) order.push(TIER_ORDER[idx - d]);
      if (idx + d < TIER_ORDER.length) order.push(TIER_ORDER[idx + d]);
    }
    if (normalIdx >= 0) {
      order.sort((a, b) => {
        const da = Math.abs(TIER_ORDER.indexOf(a) - normalIdx);
        const db = Math.abs(TIER_ORDER.indexOf(b) - normalIdx);
        return da - db;
      });
    }
    return order;
  }

  function resolvePool(tier) {
    var range = tierRanges[tier] || DEFAULT_RANGES[tier] || { minNum: 1, maxNum: 24 };
    var minN = range.minNum | 0;
    var maxN = range.maxNum | 0;
    var pool = poolForTier([tier], minN, maxN);
    if (pool.length) return { pool: pool, tier: tier };

    // 同范围换相邻档（硬过滤不丢弃）
    var order = adjacentTier(tier);
    var i;
    for (i = 0; i < order.length; i++) {
      pool = poolForTier([order[i]], minN, maxN);
      if (pool.length) return { pool: pool, tier: order[i] };
    }

    // 再放宽范围一步：max +2（不超过 24）
    var relaxedMax = Math.min(24, maxN + 2);
    if (relaxedMax > maxN) {
      pool = poolForTier([tier], minN, relaxedMax);
      if (pool.length) return { pool: pool, tier: tier, relaxed: true };
      for (i = 0; i < order.length; i++) {
        pool = poolForTier([order[i]], minN, relaxedMax);
        if (pool.length) return { pool: pool, tier: order[i], relaxed: true };
      }
    }

    return { pool: [], tier: tier, empty: true };
  }

  function updateExprBoard() {
    if (!tiles.length) {
      exprBoard.textContent = "—";
      return;
    }
    const parts = tiles.map(t => escapeHtml(t.expr));
    exprBoard.textContent = parts.join("  |  ");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function snapshot() {
    return {
      tiles: tiles.map(t => ({ id: t.id, value: t.value, expr: t.expr })),
      nextId: nextId,
    };
  }

  function pushHistory() {
    history.push(snapshot());
  }

  function resetRound(puzzle) {
    if (!puzzle || !puzzle.n) return;
    currentPuzzle = puzzle;
    casualStartedAt = Date.now();
    solved = false;
    nextId = 1;
    tiles = puzzle.n.map(v => ({ id: nextId++, value: v, expr: String(v) }));
    history = [];
    pickA = null;
    pickOp = null;
    refBox.classList.add("hidden");
    refBox.textContent = "";
    clearOpActive();
    renderTiles();
    setHint("点选一个数字（可先算任意一对）");
  }

  function clearOpActive() {
    opsEl.querySelectorAll("button").forEach(b => b.classList.remove("active"));
  }

  function renderTiles() {
    cardBoard.dataset.count = String(tiles.length);
    cardBoard.innerHTML = "";
    tiles.forEach((t, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "num-card";
      btn.dataset.id = String(t.id);
      btn.title = t.expr;
      if (idx < 4) {
        const kbd = document.createElement("span");
        kbd.className = "kbd-hint";
        kbd.textContent = String(idx + 1);
        btn.appendChild(kbd);
      }
      const val = document.createElement("span");
      val.className = "val";
      val.textContent = formatValue(t.value);
      btn.appendChild(val);
      if (t.expr !== formatValue(t.value) && t.expr !== String(t.value)) {
        const ex = document.createElement("span");
        ex.className = "expr";
        ex.textContent = t.expr;
        btn.appendChild(ex);
      }
      if (pickA === t.id) btn.classList.add("selected");
      btn.addEventListener("click", () => onTile(t.id));
      cardBoard.appendChild(btn);
    });
    updateExprBoard();
  }

  function onTile(id) {
    if (solved) return;
    const tile = tiles.find(t => t.id === id);
    if (!tile) return;

    if (pickA == null) {
      pickA = id;
      pickOp = null;
      clearOpActive();
      renderTiles();
      setHint("已选 " + tile.value + "，请选运算");
      return;
    }

    if (pickOp == null) {
      if (pickA === id) {
        pickA = null;
        renderTiles();
        setHint("点选一个数字");
        return;
      }
      pickA = id;
      renderTiles();
      setHint("已选 " + tile.value + "，请选运算");
      return;
    }

    if (pickA === id) {
      setHint("请选择另一个数字", "err");
      return;
    }

    const a = tiles.find(t => t.id === pickA);
    const b = tile;
    const result = applyOp(a.value, b.value, pickOp);
    if (result === null) {
      setHint("无法整除或除以 0，请重选运算/数字", "err");
      pickOp = null;
      clearOpActive();
      renderTiles();
      return;
    }

    pushHistory();
    const opSym = pickOp === "*" ? "×" : pickOp === "/" ? "÷" : pickOp === "-" ? "−" : "+";
    const opRaw = pickOp;
    tiles = tiles.filter(t => t.id !== a.id && t.id !== b.id);
    const neu = {
      id: nextId++,
      value: result,
      expr: "(" + a.expr + opRaw + b.expr + ")",
    };
    tiles.push(neu);
    pickA = null;
    pickOp = null;
    clearOpActive();
    renderTiles();

    const cardEl = cardBoard.querySelector('[data-id="' + neu.id + '"]');
    if (cardEl) cardEl.classList.add("pulse");

    if (tiles.length === 1) {
      if (isTargetValue(tiles[0].value)) {
        solved = true;
        setHint("得到 24！本题完成", "ok");
        onSolved();
      } else {
        setHint("结果是 " + formatValue(tiles[0].value) + "，不是 24。可上一步或重来", "err");
      }
    } else if (tiles.length === 3) {
      setHint(neu.expr + " = " + result + " · 可先算剩下两个数，再与结果合并");
    } else if (tiles.length === 2) {
      setHint("两组都算好了：把这两个结果再运算一次");
    } else {
      setHint(neu.expr + " = " + result + " · 继续选数字");
    }
  }

  function selectOp(op) {
    if (solved) return;
    if (pickA == null) {
      setHint("请先选择一个数字", "err");
      return;
    }
    pickOp = op;
    clearOpActive();
    const btn = opsEl.querySelector('[data-op="' + op + '"]');
    if (btn) btn.classList.add("active");
    const a = tiles.find(t => t.id === pickA);
    const sym = btn ? btn.textContent : op;
    setHint("已选 " + formatValue(a.value) + " " + sym + " ，再选一个数字");
  }

  opsEl.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => selectOp(btn.dataset.op));
  });

  function clearSelection() {
    pickA = null;
    pickOp = null;
    clearOpActive();
    renderTiles();
    setHint("点选一个数字");
  }

  function onPlayKeydown(e) {
    if (views.play.classList.contains("hidden")) return;
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    if (e.key === "Escape") {
      e.preventDefault();
      clearSelection();
      return;
    }
    if (e.key === "z" || e.key === "Z") {
      document.getElementById("btn-undo").click();
      return;
    }
    if (e.key === "Backspace") {
      e.preventDefault();
      document.getElementById("btn-undo").click();
      return;
    }
    if (e.key === "r" || e.key === "R") {
      document.getElementById("btn-restart").click();
      return;
    }

    const opKeys = {
      "+": "+", "-": "-", "*": "*", "/": "/",
      "NumpadAdd": "+", "NumpadSubtract": "-", "NumpadMultiply": "*", "NumpadDivide": "/",
    };
    if (opKeys[e.key]) {
      e.preventDefault();
      selectOp(opKeys[e.key]);
      return;
    }

    if (e.key >= "1" && e.key <= "4") {
      const idx = parseInt(e.key, 10) - 1;
      if (idx < tiles.length) {
        e.preventDefault();
        onTile(tiles[idx].id);
      }
    }
  }

  document.addEventListener("keydown", onPlayKeydown);

  const fracChk = document.getElementById("chk-fraction");
  if (fracChk) {
    fracChk.addEventListener("change", function () {
      allowFractionMiddle = !!fracChk.checked;
    });
  }

  function onSolved() {
    if (mode === "casual") {
      celebrate(FGB_MSG.done);
      if (typeof fgbSubmitScore === "function") fgbSubmitScore({
        gameId: "24points", mode: "casual", tier: selectedTier,
        tierLabel: TIER_LABELS[selectedTier] || selectedTier,
        metrics: { timeMs: Date.now() - casualStartedAt }
      });
      return;
    }
    done += 1;
    celebrateThen(FGB_MSG.done, advanceChallenge, 480);
  }

  function advanceChallenge() {
    remaining.shift();
    if (!remaining.length) {
      finishChallenge();
      return;
    }
    updatePlayChrome();
    resetRound(remaining[0]);
  }

  function startTimer() {
    stopTimer();
    startedAt = Date.now();
    timerId = window.setInterval(() => {
      document.getElementById("timer-text").textContent = fmtTime(Date.now() - startedAt);
    }, 250);
  }

  function stopTimer() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  function pickRandomPuzzle() {
    const resolved = resolvePool(selectedTier);
    const pool = resolved.pool;
    if (!pool || !pool.length) return null;
    return pool[(Math.random() * pool.length) | 0];
  }

  function notifyEmptyPool() {
    var msg = "该档在当前数字范围内无题，请在管理端调大 min/max";
    setHint(msg, "err");
    if (window.FGBUI && FGBUI.toast) FGBUI.toast(msg, "err");
  }

  function startCasual() {
    ensureDifficulty(function () {
      var puzzle = pickRandomPuzzle();
      if (!puzzle) {
        notifyEmptyPool();
        show("setup");
        return;
      }
      mode = "casual";
      show("play");
      updatePlayChrome();
      resetRound(puzzle);
    });
  }

  function startChallenge() {
    ensureDifficulty(function () {
      mode = "challenge";
      done = 0;
      const resolved = resolvePool(selectedTier);
      const pool = resolved.pool;
      if (!pool.length) {
        notifyEmptyPool();
        show("setup");
        return;
      }
      const take = Math.min(challengeCount, pool.length);
      remaining = shuffle(pool).slice(0, take).map(p => ({
        n: p.n.slice(),
        h: p.h,
        t: p.t,
      }));
      challengeTotal = remaining.length;
      show("play");
      updatePlayChrome();
      startTimer();
      resetRound(remaining[0]);
    });
  }

  function startFromSetup() {
    if (mode === "challenge") startChallenge();
    else startCasual();
  }

  function finishChallenge() {
    stopTimer();
    const elapsed = Date.now() - startedAt;
    document.getElementById("st-total").textContent = String(challengeTotal);
    document.getElementById("st-done").textContent = String(done);
    document.getElementById("st-time").textContent = fmtTime(elapsed);
    const rate = challengeTotal ? Math.round((done / challengeTotal) * 100) : 0;
    document.getElementById("st-rate").textContent = rate + "%";
    document.getElementById("result-sub").textContent =
      done === challengeTotal ? "全部完成，漂亮！" : "本局挑战结束";
    show("result");
    celebrate(FGB_MSG.sessionDone);
    if (typeof fgbSubmitScore === "function") fgbSubmitScore({
      gameId: "24points", mode: "challenge", tier: selectedTier,
      tierLabel: TIER_LABELS[selectedTier] || selectedTier,
      metrics: { done: done, total: challengeTotal, timeMs: elapsed, skip: 0 }
    });
  }

  function updatePlayChrome() {
    const tierName = TIER_LABELS[selectedTier] || "";
    document.getElementById("play-mode-label").textContent =
      (mode === "casual" ? "休闲" : "挑战") + (tierName ? " · " + tierName : "");
    const prog = document.getElementById("play-progress");
    if (mode === "challenge") {
      const cur = Math.min(done + 1, challengeTotal);
      prog.textContent = cur + " / " + challengeTotal;
      document.getElementById("play-timer").classList.remove("hidden");
      document.getElementById("casual-extra").classList.add("hidden");
    } else {
      prog.textContent = "";
      document.getElementById("play-timer").classList.add("hidden");
      document.getElementById("casual-extra").classList.remove("hidden");
    }
  }

  // buttons
  document.getElementById("btn-casual").addEventListener("click", () => openSetup("casual"));
  document.getElementById("btn-challenge").addEventListener("click", () => openSetup("challenge"));
  document.getElementById("btn-setup-back").addEventListener("click", () => show("home"));
  document.getElementById("btn-start").addEventListener("click", startFromSetup);

  document.querySelectorAll("#tier-choices button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#tier-choices button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedTier = btn.dataset.tier;
      updateDiffDesc();
    });
  });

  document.querySelectorAll("#count-choices button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#count-choices button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      challengeCount = Number(btn.dataset.n);
    });
  });

  document.getElementById("btn-undo").addEventListener("click", () => {
    if (solved && mode === "challenge") return;
    if (!history.length) {
      setHint("没有可回退的步骤", "err");
      return;
    }
    const snap = history.pop();
    tiles = snap.tiles.map(t => ({ id: t.id, value: t.value, expr: t.expr }));
    nextId = snap.nextId;
    pickA = null;
    pickOp = null;
    solved = false;
    clearOpActive();
    renderTiles();
    setHint("已回退 · 点选一个数字");
  });

  document.getElementById("btn-restart").addEventListener("click", () => {
    if (!currentPuzzle) return;
    resetRound({ n: currentPuzzle.n.slice(), h: currentPuzzle.h });
  });

  document.getElementById("btn-exit").addEventListener("click", () => {
    if (window.__FGB_IS_DAILY__ || (window.FGBDaily && FGBDaily.isDaily && FGBDaily.isDaily())) {
      if (window.FGBDaily && FGBDaily.notifyAbort) FGBDaily.notifyAbort();
      return;
    }
    if (mode === "challenge") {
      askConfirm(FGB_MSG.exitConfirm, finishChallenge);
      return;
    }
    show("home");
  });

  document.getElementById("btn-next").addEventListener("click", () => {
    var puzzle = pickRandomPuzzle();
    if (!puzzle) {
      notifyEmptyPool();
      return;
    }
    resetRound(puzzle);
  });

  document.getElementById("btn-hint").addEventListener("click", () => {
    if (!currentPuzzle) return;
    refBox.textContent = "参考：" + (currentPuzzle.h || "（无）");
    refBox.classList.remove("hidden");
  });

  document.getElementById("btn-again").addEventListener("click", () => openSetup("challenge"));
  document.getElementById("btn-home").addEventListener("click", () => {
    stopTimer();
    show("home");
  });

  updateDiffDesc();
  ensureDifficulty(function () {
    updateDiffDesc();
    if (window.__FGB_IS_DAILY__ || /(?:^|[?&])daily=1(?:&|$)/.test(location.search || "")) {
      var dq = window.__FGB_DAILY_Q__ || {};
      if (!dq.tier) dq.tier = (new URLSearchParams(location.search || "")).get("tier") || "normal";
      if (dq.tier) selectedTier = dq.tier;
      startCasual();
    } else {
      show("home");
    }
  });
  } // end boot

  if (homeView) {
    const tip = document.createElement("p");
    tip.className = "sub";
    tip.id = "bank-loading";
    tip.textContent = "题库加载中…";
    homeView.appendChild(tip);
  }

  fetch("bank.json", { cache: "no-store" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (bank) {
      if (!Array.isArray(bank) || !bank.length) throw new Error("题库为空");
      var loading = document.getElementById("bank-loading");
      if (loading) loading.remove();
      boot(bank);
    })
    .catch(function (err) {
      showFatal("题库加载失败：" + (err && err.message ? err.message : String(err)) + "。请确认同目录存在 bank.json，或重新执行 scripts\\\\build.bat。");
    });
})();
</script>
</body>
</html>
'''


def main() -> None:
    root = repo_root()
    build_play, web_play, _dist_play = points_page_paths("play.html")
    parser = argparse.ArgumentParser(description="Generate 24-point play HTML.")
    parser.add_argument("--solutions", default=str(root / "output" / "solutions.txt"))
    parser.add_argument("--out", default=str(build_play))
    parser.add_argument("--dist", default=str(web_play))
    args = parser.parse_args()

    solutions_path = Path(args.solutions)
    if not solutions_path.is_file():
        raise SystemExit("missing %s" % solutions_path)

    t0 = time.perf_counter()
    groups = parse_solutions(solutions_path)
    scored = []
    for nums, exprs in groups:
        hardness = compute_hardness(nums, exprs)
        scored.append(
            (
                hardness,
                {"n": list(nums), "h": _pick_ref_expr(exprs)},
            )
        )
    bank = assign_tiers(scored)

    html = build_play_html()
    out_path = Path(args.out)
    dist_path = Path(args.dist)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dist_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    dist_path.write_text(html, encoding="utf-8")

    bank_json = json.dumps(bank, ensure_ascii=False, separators=(",", ":"))
    out_bank = out_path.with_name("bank.json")
    dist_bank = dist_path.with_name("bank.json")
    out_bank.write_text(bank_json, encoding="utf-8")
    dist_bank.write_text(bank_json, encoding="utf-8")

    print(
        "Wrote %s + %s (%.1f KB bank, %d puzzles, %.2fs)"
        % (
            out_path,
            out_bank.name,
            out_bank.stat().st_size / 1024,
            len(bank),
            time.perf_counter() - t0,
        )
    )
    print("Wrote %s + %s" % (dist_path, dist_bank.name))


if __name__ == "__main__":
    main()
