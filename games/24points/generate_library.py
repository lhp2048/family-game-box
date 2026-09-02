#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 output/solutions.txt 与 summary.txt 生成可浏览的静态 HTML。"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

_GAMES = Path(__file__).resolve().parents[1]
if str(_GAMES) not in sys.path:
    sys.path.insert(0, str(_GAMES))

from common.paths import points_page_paths, repo_root

HEADER_RE = re.compile(
    r"^\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\s+\((\d+)\s+solutions\)\s*$"
)


def parse_summary(path: Path) -> Dict[str, str]:
    stats: Dict[str, str] = {}
    if not path.is_file():
        return stats
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        stats[key.strip()] = val.strip()
    return stats


def parse_solutions(path: Path) -> List[Tuple[List[int], List[str]]]:
    groups: List[Tuple[List[int], List[str]]] = []
    current_nums: List[int] = []
    current_exprs: List[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        m = HEADER_RE.match(line)
        if m:
            if current_nums:
                groups.append((current_nums, current_exprs))
            current_nums = [int(m.group(i)) for i in range(1, 5)]
            current_exprs = []
            continue
        if line.startswith("  "):
            current_exprs.append(line.strip())

    if current_nums:
        groups.append((current_nums, current_exprs))
    return groups


def build_html(stats: Dict[str, str], groups: List[Tuple[List[int], List[str]]]) -> str:
    payload = [{"n": n, "e": e} for n, e in groups]
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    total = stats.get("Total combos", str(sum(1 for _ in groups) + int(stats.get("Unsolvable combos", "0") or 0)))
    solvable = stats.get("Solvable combos", str(len(groups)))
    unsolvable = stats.get("Unsolvable combos", "")
    expr_count = stats.get("Total expressions", str(sum(len(e) for _, e in groups)))
    rng = stats.get("Range", "0 .. 24 (inclusive)")

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>24 点 · 整数解法库</title>
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
  --shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
  --radius: 18px;
  --display: "Fraunces", "Songti SC", "Palatino Linotype", serif;
  --sans: "DM Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif;
  --mono: "Cascadia Code", "Sarasa Mono SC", "Consolas", monospace;
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
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.2;
  background-image:
    linear-gradient(rgba(232,242,236,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(232,242,236,0.03) 1px, transparent 1px);
  background-size: 28px 28px;
}
.wrap {
  position: relative;
  width: min(960px, calc(100% - 2rem));
  margin: 0 auto;
  padding: 2.5rem 0 4rem;
}
.brand {
  font-family: var(--display);
  font-size: clamp(2.8rem, 8vw, 4.5rem);
  line-height: 0.95;
  letter-spacing: -0.02em;
  margin: 0 0 0.4rem;
}
.brand em {
  font-style: italic;
  color: var(--accent);
}
.lede {
  margin: 0 0 1.6rem;
  max-width: 36rem;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 1.55;
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.4rem;
}
.stat {
  padding: 0.9rem 1rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow);
}
.stat b {
  display: block;
  font-family: var(--display);
  font-size: 1.55rem;
  line-height: 1;
  margin-bottom: 0.35rem;
}
.stat span {
  color: var(--muted);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.search {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr)) auto auto;
  gap: 0.55rem;
  padding: 0.9rem;
  border: 1px solid var(--line);
  border-radius: calc(var(--radius) + 4px);
  background: var(--panel);
  box-shadow: var(--shadow);
  margin-bottom: 0.85rem;
}
.search input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.75rem 0.8rem;
  font: inherit;
  font-size: 1.05rem;
  text-align: center;
  background: rgba(255,255,255,.04);
  color: var(--ink);
}
.search input:focus {
  outline: 2px solid rgba(62, 207, 142, 0.35);
  border-color: var(--accent);
}
.search button {
  border: 0;
  border-radius: 12px;
  padding: 0 1.1rem;
  font: inherit;
  font-weight: 700;
  color: #062016;
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
  cursor: pointer;
  white-space: nowrap;
}
.search button.ghost {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--line);
  font-weight: 600;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.1rem;
  align-items: center;
  color: var(--muted);
  font-size: 0.92rem;
  margin-bottom: 1rem;
}
.meta strong { color: var(--ink); }
.list { display: grid; gap: 0.7rem; }
.card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255,252,246,0.9);
  overflow: hidden;
  animation: rise 0.35s ease both;
}
@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}
.card summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 0.95rem 1.05rem;
  font-weight: 600;
}
.card summary::-webkit-details-marker { display: none; }
.nums {
  font-family: var(--display);
  font-size: 1.35rem;
  letter-spacing: 0.02em;
}
.badge {
  color: var(--accent);
  background: rgba(62, 207, 142, 0.1);
  border-radius: 999px;
  padding: 0.25rem 0.7rem;
  font-size: 0.82rem;
  font-weight: 700;
}
.exprs {
  margin: 0;
  padding: 0 1.05rem 1rem;
  border-top: 1px solid var(--line);
  max-height: 280px;
  overflow: auto;
}
.exprs code {
  display: block;
  font-family: var(--mono);
  font-size: 0.86rem;
  padding: 0.45rem 0;
  border-bottom: 1px dashed rgba(232,242,236,0.12);
  white-space: nowrap;
}
.exprs code:last-child { border-bottom: 0; }
.empty, .hint {
  padding: 1.4rem 1.1rem;
  border: 1px dashed rgba(232,242,236,0.2);
  border-radius: var(--radius);
  color: var(--muted);
  background: rgba(255,252,246,0.55);
}
.hint { margin-bottom: 1rem; }
footer {
  margin-top: 2rem;
  color: var(--muted);
  font-size: 0.85rem;
}
@media (max-width: 720px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .search { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .search button { min-height: 2.8rem; }
}
</style>
</head>
<body>
  <div class="wrap">
    <h1 class="brand">24<em>点</em></h1>
    <p class="lede">整数四则运算解法库。范围 """ + _esc(rng) + """；仅整除合法。输入 4 个数查询，或浏览全部有解组合。</p>
    <p style="margin:0 0 1.2rem"><a href="/" style="color:var(--accent);font-weight:600;text-decoration:none">← 返回大厅</a></p>

    <div class="stats">
      <div class="stat"><b id="stat-solvable">""" + _esc(solvable) + """</b><span>有解组合</span></div>
      <div class="stat"><b id="stat-exprs">""" + _esc(expr_count) + """</b><span>解法条数</span></div>
      <div class="stat"><b id="stat-total">""" + _esc(total) + """</b><span>全部组合</span></div>
      <div class="stat"><b id="stat-unsolvable">""" + _esc(unsolvable or "—") + """</b><span>无解组合</span></div>
    </div>

    <form class="search" id="search-form" autocomplete="off">
      <input id="n0" inputmode="numeric" placeholder="0" maxlength="2" aria-label="数1">
      <input id="n1" inputmode="numeric" placeholder="0" maxlength="2" aria-label="数2">
      <input id="n2" inputmode="numeric" placeholder="0" maxlength="2" aria-label="数3">
      <input id="n3" inputmode="numeric" placeholder="0" maxlength="2" aria-label="数4">
      <button type="submit">查询</button>
      <button type="button" class="ghost" id="btn-clear">清空</button>
    </form>

    <p class="hint">未输入时显示前 40 组有解组合；查询会按升序匹配（顺序无关）。点击条目展开全部表达式。</p>
    <div class="meta">
      <span>显示 <strong id="shown-count">0</strong> / <strong id="match-count">0</strong> 组</span>
      <span id="query-label"></span>
    </div>
    <div class="list" id="list"></div>
    <div class="empty" id="empty" hidden>没有匹配的有解组合。</div>
    <div class="meta" id="more-wrap" hidden>
      <button type="button" class="ghost" id="btn-more" style="border:1px solid var(--line);border-radius:12px;padding:0.55rem 1rem;background:rgba(255,255,255,.04);cursor:pointer;font:inherit;font-weight:600;color:var(--ink)">加载更多</button>
    </div>
    <footer>数据来自 solutions.txt · <a href="play.html" style="color:var(--accent);font-weight:600;text-decoration:none">去玩 24 点</a> · 整数运算 24 点</footer>
  </div>

<script id="data" type="application/json">""" + data_json + """</script>
<script>
(function () {
  const DATA = JSON.parse(document.getElementById("data").textContent);
  const listEl = document.getElementById("list");
  const emptyEl = document.getElementById("empty");
  const shownEl = document.getElementById("shown-count");
  const matchEl = document.getElementById("match-count");
  const queryLabel = document.getElementById("query-label");
  const moreWrap = document.getElementById("more-wrap");
  const inputs = [0,1,2,3].map(i => document.getElementById("n" + i));

  let filtered = DATA.slice();
  let shown = 0;
  const PAGE = 40;

  function normKey(arr) {
    return arr.slice().sort((a,b) => a - b).join(",");
  }

  const index = new Map();
  DATA.forEach((item, i) => index.set(normKey(item.n), i));

  function readQuery() {
    const vals = inputs.map(el => el.value.trim());
    if (vals.every(v => v === "")) return null;
    if (vals.some(v => v === "" || !/^\\d{1,2}$/.test(v))) return "invalid";
    const nums = vals.map(Number);
    if (nums.some(n => n < 0 || n > 24)) return "range";
    return nums;
  }

  function renderReset(items) {
    filtered = items;
    shown = 0;
    listEl.innerHTML = "";
    matchEl.textContent = String(filtered.length);
    emptyEl.hidden = filtered.length > 0;
    moreWrap.hidden = true;
    renderMore();
  }

  function renderMore() {
    const end = Math.min(shown + PAGE, filtered.length);
    const frag = document.createDocumentFragment();
    for (let i = shown; i < end; i++) {
      const item = filtered[i];
      const details = document.createElement("details");
      details.className = "card";
      details.style.animationDelay = ((i - shown) * 20) + "ms";
      const summary = document.createElement("summary");
      const nums = document.createElement("span");
      nums.className = "nums";
      nums.textContent = item.n.join(" · ");
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = item.e.length + " 解";
      summary.appendChild(nums);
      summary.appendChild(badge);
      const box = document.createElement("div");
      box.className = "exprs";
      item.e.forEach(expr => {
        const code = document.createElement("code");
        code.textContent = expr;
        box.appendChild(code);
      });
      details.appendChild(summary);
      details.appendChild(box);
      frag.appendChild(details);
    }
    listEl.appendChild(frag);
    shown = end;
    shownEl.textContent = String(shown);
    moreWrap.hidden = shown >= filtered.length;
  }

  function applySearch() {
    const q = readQuery();
    if (q === null) {
      queryLabel.textContent = "浏览模式";
      renderReset(DATA);
      return;
    }
    if (q === "invalid") {
      queryLabel.textContent = "请输入 0–24 的四个整数";
      renderReset([]);
      return;
    }
    if (q === "range") {
      queryLabel.textContent = "数字需在 0–24";
      renderReset([]);
      return;
    }
    const key = normKey(q);
    const idx = index.get(key);
    queryLabel.textContent = "查询 " + q.join(", ") + " → [" + key.replace(/,/g, ", ") + "]";
    if (idx == null) {
      renderReset([]);
      return;
    }
    renderReset([DATA[idx]]);
  }

  document.getElementById("search-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    applySearch();
  });
  document.getElementById("btn-clear").addEventListener("click", function () {
    inputs.forEach(el => { el.value = ""; });
    inputs[0].focus();
    applySearch();
  });
  document.getElementById("btn-more").addEventListener("click", renderMore);

  inputs.forEach((el, i) => {
    el.addEventListener("input", function () {
      el.value = el.value.replace(/[^\\d]/g, "").slice(0, 2);
      if (el.value.length >= 2 && i < 3) inputs[i + 1].focus();
    });
  });

  applySearch();
})();
</script>
</body>
</html>
"""


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main() -> None:
    root = repo_root()
    build_lib, web_lib, _dist_lib = points_page_paths("library.html")
    parser = argparse.ArgumentParser(description="Generate static HTML from 24-point solutions.")
    parser.add_argument("--solutions", default=str(root / "output" / "solutions.txt"))
    parser.add_argument("--summary", default=str(root / "output" / "summary.txt"))
    parser.add_argument("--out", default=str(build_lib))
    parser.add_argument("--dist", default=str(web_lib), help="runtime web path")
    args = parser.parse_args()

    solutions_path = Path(args.solutions)
    summary_path = Path(args.summary)
    out_path = Path(args.out)
    dist_path = Path(args.dist)

    if not solutions_path.is_file():
        raise SystemExit("missing %s — run solve_24.py first" % solutions_path)

    t0 = time.perf_counter()
    stats = parse_summary(summary_path)
    groups = parse_solutions(solutions_path)
    html = build_html(stats, groups)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    dist_path.parent.mkdir(parents=True, exist_ok=True)
    dist_path.write_text(html, encoding="utf-8")

    elapsed = time.perf_counter() - t0
    print("Wrote %s (%.1f KB)" % (out_path, out_path.stat().st_size / 1024))
    print("Wrote %s" % dist_path)
    print("Groups: %d  elapsed: %.2fs" % (len(groups), elapsed))


if __name__ == "__main__":
    main()
