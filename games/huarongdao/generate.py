#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成华容道（经典 Klotski）页面。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.game_common import build_page, inject_lobby_link, run_generator
from common.paths import game_page_paths

SLUG = "huarongdao"
HERE = Path(__file__).resolve().parent

EXTRA_CSS = r"""
.hrg-hero { text-align: center; margin-bottom: 1rem; }
.hrg-tag {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--muted);
  margin-bottom: 0.35rem;
}
.hrg-mode-grid { display: grid; gap: 0.75rem; }
.hrg-level-list { display: grid; gap: 0.55rem; max-height: min(58vh, 520px); overflow: auto; }
.hrg-level-btn {
  text-align: left;
  border: 2px solid var(--line);
  border-radius: 16px;
  padding: 0.75rem 0.9rem;
  background: #fff;
  cursor: pointer;
  font: inherit;
  color: var(--ink);
  box-shadow: 0 4px 0 rgba(26, 43, 60, 0.05);
}
.hrg-level-btn strong { display: block; font-family: var(--display); font-size: 1.05rem; }
.hrg-level-btn span { display: block; margin-top: 0.2rem; font-size: 0.82rem; color: var(--muted); }
.hrg-level-btn.is-locked { opacity: 0.45; cursor: not-allowed; }
.hrg-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  justify-content: center;
  margin-bottom: 0.55rem;
}
.hrg-toolbar button {
  border: 2px solid rgba(26, 43, 60, 0.1);
  border-radius: 999px;
  min-height: 42px;
  padding: 0.45rem 0.85rem;
  font: inherit;
  font-weight: 700;
  background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
  box-shadow: 0 3px 0 rgba(26, 43, 60, 0.06);
  cursor: pointer;
}
.hrg-meta {
  text-align: center;
  font-size: 0.88rem;
  color: var(--muted);
  margin: 0 0 0.45rem;
  min-height: 1.2em;
}
.hrg-hint {
  text-align: center;
  font-size: 0.82rem;
  color: var(--accent-deep);
  min-height: 1.2em;
  margin: 0 0 0.35rem;
}
.hrg-board-wrap {
  display: flex;
  justify-content: center;
  margin: 0.25rem 0 0.65rem;
}
.hrg-board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: repeat(5, 1fr);
  gap: clamp(3px, 0.8vw, 6px);
  width: min(92vw, 360px);
  aspect-ratio: 4 / 5;
  padding: clamp(6px, 1.2vw, 10px);
  border-radius: 18px;
  border: 2px solid rgba(255, 159, 67, 0.35);
  background: linear-gradient(165deg, #fff8f0 0%, #ffe8d4 45%, #fff5eb 100%);
  box-shadow: 0 12px 32px rgba(45, 62, 90, 0.12);
  position: relative;
  touch-action: none;
}
.hrg-exit {
  grid-row: 5;
  grid-column: 2 / span 2;
  border: 2px dashed rgba(46, 204, 113, 0.55);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 800;
  color: #1a7a4a;
  background: rgba(232, 255, 244, 0.55);
  pointer-events: none;
  z-index: 0;
}
.hrg-piece {
  z-index: 1;
  border: 2px solid rgba(26, 43, 60, 0.1);
  border-radius: 14px;
  margin: 0;
  padding: 0;
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--display);
  font-weight: 800;
  font-size: clamp(0.95rem, 4vw, 1.25rem);
  color: #1a2b3c;
  box-shadow: 0 4px 0 rgba(26, 43, 60, 0.08);
  transition: transform 0.08s ease;
}
.hrg-piece:active { cursor: grabbing; }
.hrg-piece.is-selected {
  outline: 3px solid rgba(255, 159, 67, 0.65);
  transform: translateY(-2px);
}
.hrg-cao {
  background: linear-gradient(180deg, #ffd4a8 0%, #ffb07a 100%);
  color: #6b2f10;
}
.hrg-v {
  background: linear-gradient(180deg, #fffef9 0%, #f5efe0 100%);
}
.hrg-guan {
  background: linear-gradient(180deg, #fff8eb 0%, #ffe4b8 100%);
}
.hrg-s {
  background: linear-gradient(180deg, #e8fff4 0%, #c8f5e0 100%);
  font-size: clamp(0.82rem, 3.2vw, 1rem);
}
.hrg-piece-label { pointer-events: none; }
"""

BODY = r"""
  <section id="view-home">
    <div class="hrg-hero">
      <p class="hrg-tag">经典滑块</p>
      <h1>华容<em>道</em></h1>
      <p class="sub">曹操逃出底部出口。拖动或方向键移动棋子；同一手势连续挪动只计 1 步。</p>
    </div>
    <div class="card hrg-mode-grid">
      <button type="button" class="mode-btn" id="btn-campaign">
        <strong>闯关模式</strong>
        <span>18 关 · 解锁制 · 星级评价</span>
      </button>
      <button type="button" class="mode-btn" id="btn-classic">
        <strong>经典十局</strong>
        <span>名局挑战 · 按最少步数排行</span>
      </button>
    </div>
    {lobby_back_link()}
  </section>

  <section id="view-pick" class="hidden">
    <h1 id="pick-title">选关</h1>
    <p class="sub">布局来自开源 jeantimex/klotski（MIT），最优步数为宏步（换子 +1）。</p>
    <div class="card">
      <div class="hrg-level-list" id="level-list"></div>
      <div style="height:.65rem"></div>
      <button type="button" class="ghost" id="btn-pick-back" style="width:100%">返回</button>
    </div>
  </section>

  <section id="view-play" class="hidden">
    <h1 id="play-title">对局</h1>
    <p class="hrg-meta" id="hrg-meta"></p>
    <div class="card play-card">
      <div class="hrg-toolbar">
        <button type="button" id="btn-undo">撤销</button>
        <button type="button" id="btn-restart">重来</button>
        <button type="button" id="btn-hint">看解法</button>
        <button type="button" id="btn-exit-play">退出</button>
      </div>
      <p class="hrg-hint" id="hrg-hint"></p>
      <div class="hrg-board-wrap">
        <div class="hrg-board" id="hrg-board" aria-label="华容道棋盘"></div>
      </div>
      <p class="hint">步数 <strong id="hrg-steps">0</strong> · 曹操到达底部中间出口即胜</p>
    </div>
  </section>

  <section id="view-result" class="hidden">
    <h1>通关</h1>
    <div class="card">
      <ul class="stats-list">
        <li><span>本局步数</span><strong id="res-steps">0</strong></li>
        <li><span>最少步数</span><strong id="res-opt">0</strong></li>
        <li><span>星级</span><strong id="res-stars">★★★</strong></li>
        <li><span>用时</span><strong id="res-time">00:00</strong></li>
      </ul>
      <button type="button" class="primary" id="btn-again">再来一局</button>
      <div style="height:.55rem"></div>
      <button type="button" class="ghost" id="btn-back-pick" style="width:100%">选关</button>
    </div>
  </section>
"""


def ensure_layouts() -> dict:
    layouts_path = HERE / "layouts.json"
    if not layouts_path.is_file():
        subprocess.check_call(["node", str(HERE / "compute_layouts.js")], cwd=str(HERE))
    return json.loads(layouts_path.read_text(encoding="utf-8"))


def build_script(layouts: dict) -> str:
    game_js = (HERE / "game_script.js").read_text(encoding="utf-8")
    data_js = json.dumps(layouts, ensure_ascii=False, separators=(",", ":"))
    return (
        "var HRD_LAYOUTS = %s;\n" % data_js
        + game_js
    )


def build_html() -> str:
    layouts = ensure_layouts()
    script = build_script(layouts)
    html = build_page(
        "华容道",
        EXTRA_CSS,
        inject_lobby_link(BODY),
        script,
        wide=False,
        game_skin=SLUG,
        game_title="华容道",
    )
    html = html.replace(
        '<script src="/js/fgb-shell.js"></script>',
        '<script src="/js/fgb-shell.js"></script>\n<script src="hrd-solver.js"></script>',
        1,
    )
    return html


def copy_solver(web_dir: Path) -> None:
    src = HERE / "klotski-ref.js"
    dst = web_dir / "hrd-solver.js"
    shutil.copy2(src, dst)


def main() -> None:
    build, web, _dist = game_page_paths(SLUG)
    parser = argparse.ArgumentParser(description="Generate 华容道 HTML.")
    parser.add_argument("--out", default=str(build))
    parser.add_argument("--dist", default=str(web))
    args = parser.parse_args()
    web_dir = Path(args.dist).parent
    web_dir.mkdir(parents=True, exist_ok=True)
    copy_solver(web_dir)
    run_generator(build_html, args.out, args.dist, SLUG)


if __name__ == "__main__":
    main()
