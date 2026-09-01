# 家庭竞技厅壳层 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将大厅、两榜、每日壳重建为「赛季看板」竞技厅信息架构，并用 `GET /api/v1/lobby/summary` 驱动战绩条与今日榜摘要。

**Architecture:** 新增 `app/lobby.py` 拼装汇总；壳页改 DOM（战绩条 / 分栏 / 列表行 / 领奖台）；扩展 `fgb-theme.css` 竞技组件；`FGB.loadLobbySummary()` 供大厅与每日准备页使用。不改游戏首页、不改闯关 iframe 协议与计分排序键。

**Tech Stack:** FastAPI、pytest、静态 HTML/CSS/JS（现有 `fgb-client.js`）。

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-01-lobby-arena-design.md`
- 分支：继续 `feature/lobby-theme`（或另开 `feature/lobby-arena`）；勿提交无关 `family-product.json` 噪声
- 挑战榜排序不变：通关优先 → `stagesDone` 降序 → `totalTimeMs` 升序
- 游戏首页 / 对局 / iframe postMessage 不动
- 令牌沿用现有深炭绿；禁止紫粉霓虹、奶油纸、报纸风
- PowerShell 下多命令用 `;` 不用 `&&`

## File map

| 文件 | 职责 |
|------|------|
| `app/lobby.py` | `get_lobby_summary(terminal_id: Optional[str]) -> dict` |
| `app/main.py` | `GET /api/v1/lobby/summary` |
| `tests/test_lobby_summary.py` | 单元 + HTTP |
| `web/js/fgb-client.js` | `loadLobbySummary` |
| `web/css/fgb-theme.css` | `.fgb-stat-strip` `.fgb-podium*` `.fgb-arena-split` `.fgb-game-row` `.fgb-cta-daily` |
| `web/index.html` | 赛季看板 DOM + 绑定 summary |
| `web/leaderboard.html` | 领奖台 + 表 |
| `web/daily-leaderboard.html` | 同上 |
| `web/daily.html` | 准备页摘要 / 结算强调 |

---

### Task 1: `app/lobby.py` 汇总逻辑（TDD）

**Files:**
- Create: `app/lobby.py`
- Create: `tests/test_lobby_summary.py`
- Modify: （本任务不改 `main.py`；纯模块测试）

**Interfaces:**
- Consumes: `app.daily_challenges.ensure_today`, `local_today`；`app.daily_runs.leaderboard`；`app.daily_runs` 内部 runs（可在 `lobby.py` 用 `load_json("daily_runs.json")` 或抽 `daily_runs.list_runs_for_terminal(day, tid)`——优先在 `lobby.py` 读 store，避免大改 daily_runs）
- Consumes: `app.scores` entries via `load_json` / 新增 `scores.latest_for_terminal(terminal_id)`（推荐加小函数）
- Produces: `get_lobby_summary(terminal_id: Optional[str]) -> Dict[str, Any]` 字段同 spec §5.2

- [ ] **Step 1: 写失败测试**

```python
# tests/test_lobby_summary.py
import uuid
import pytest
from app import lobby
from app.terminals import register_terminal
from app.daily_challenges import ensure_today
from app import daily_runs
from app import scores


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_summary_empty_no_terminal():
    data = lobby.get_lobby_summary(None)
    assert "date" in data
    assert data["me"]["nickname"] is None
    assert data["me"]["dailyRank"] is None
    assert data["podium"] == []
    assert data["recent"] is None
    assert data["daily"]["cta"] == "start"


def test_summary_podium_and_gap():
    ensure_today()
    t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
    register_terminal(t1, "甲")
    register_terminal(t2, "乙")
    r1 = daily_runs.start_run(t1)
    daily_runs.patch_run(t1, r1["runId"], {"action": "finish", "totalTimeMs": 100000, "stage": {"gameId": "schulte", "tier": "normal", "timeMs": 100000, "completed": True}})
    # 补齐 stagesDone：按 combo 关数循环 finish 或多次 stage_done——按项目现有 test_daily_runs 写法凑满 finished
    r2 = daily_runs.start_run(t2)
    daily_runs.patch_run(t2, r2["runId"], {"action": "finish", "totalTimeMs": 120000, "stage": {"gameId": "schulte", "tier": "normal", "timeMs": 120000, "completed": True}})
    data = lobby.get_lobby_summary(t2)
    assert data["me"]["dailyRank"] is not None
    assert data["podium"]
    assert data["me"]["gapLabel"]
```

实现时以 `tests/test_daily_runs.py` 为范本，保证 `finished` 记录进入 `leaderboard()`。

- [ ] **Step 2: 跑测确认失败**

Run: `pytest tests/test_lobby_summary.py -v`  
Expected: FAIL（`app.lobby` 不存在或 `get_lobby_summary` 缺失）

- [ ] **Step 3: 实现 `scores.latest_for_terminal`（若尚无）**

在 `app/scores.py` 末尾：

```python
def latest_for_terminal(terminal_id: str) -> Optional[Dict[str, Any]]:
    if not terminal_id:
        return None
    best = None
    for item in _load_entries():
        if item.get("terminalId") != terminal_id:
            continue
        if best is None or str(item.get("playedAt") or "") > str(best.get("playedAt") or ""):
            best = item
    if not best:
        return None
    return {
        "gameId": best.get("gameId", ""),
        "gameTitle": _GAME_TITLE.get(best.get("gameId", ""), best.get("gameId", "")),
        "display": best.get("display", ""),
        "playedAt": best.get("playedAt"),
    }
```

- [ ] **Step 4: 实现 `app/lobby.py`**

要点：

```python
def get_lobby_summary(terminal_id: Optional[str] = None) -> Dict[str, Any]:
    combo = ensure_today()
    day = combo["date"]
    stage_count = len(combo.get("stages") or [])
    board = daily_runs.leaderboard(date=day, limit=50)
    items = board.get("items") or []
    podium = []
    for idx, it in enumerate(items[:3], start=1):
        podium.append({
            "rank": idx,
            "nickname": it.get("nickname") or "",
            "status": it.get("status"),
            "stagesDone": int(it.get("stagesDone") or 0),
            "totalTimeMs": int(it.get("totalTimeMs") or 0),
            "display": _fmt_daily_display(it),
        })
    me = _build_me(terminal_id, day, stage_count, items, podium)
    daily = _build_daily(terminal_id, day, stage_count, me)
    recent = scores.latest_for_terminal(terminal_id) if terminal_id else None
    return {"date": day, "me": me, "podium": podium, "daily": daily, "recent": recent}
```

`gapLabel` 规则：
- 无我 / 无第 1 → `"—"`
- 双方 `finished` → 若 `meMs > firstMs`：`落后 {秒}s`；相等：`并列第1`；更小：`领先 {秒}s`；并设 `gapToFirstMs = meMs - firstMs`
- 否则用关数差：`少 N 关` / `多 N 关` / `"—"`

`cta` 规则：
- 今日无该 terminal 的 run → `start`，`myProgressLabel=未开始`
- 存在 `running` → `continue`，`进行中 {done}/{stageCount}`
- 最新为 `finished` → `view`，`已通关`
- 最新为 `exited` → `start`，`已退出 {done}/{stageCount}`（按钮文案「再挑战」由前端映射）

查找「我的榜名次」：在 `items` 里按 `nickname` **且** 若 run 带 terminalId 则优先匹配 terminal（leaderboard 项若无 terminalId，则用 nickname 匹配 `get_terminal`）。若 leaderboard 条目无 terminalId，在 `lobby` 内直接扫 `daily_runs.json` 的 runs 算个人最新状态与榜位（与 leaderboard 同排序键对「该 terminal 今日最佳 ended run」定位）。

简化实现（推荐）：  
1) 从 runs 取该 terminal 今日所有非 running 的 ended runs，取排序最优一条为「我的成绩」；  
2) 用完整 leaderboard `items` 找同一 `runId` 得 `dailyRank`；找不到则 `null` /「未上榜」。

- [ ] **Step 5: 跑测通过**

Run: `pytest tests/test_lobby_summary.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/lobby.py app/scores.py tests/test_lobby_summary.py
git commit -m "feat(lobby): add lobby summary assembler"
```

---

### Task 2: HTTP 路由

**Files:**
- Modify: `app/main.py`（在 daily leaderboard 路由附近）
- Modify: `tests/test_lobby_summary.py`（追加 TestClient 用例）

**Interfaces:**
- Consumes: `lobby.get_lobby_summary`
- Produces: `GET /api/v1/lobby/summary` → 200 JSON

- [ ] **Step 1: 追加 API 测试**

```python
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_lobby_summary_http():
    r = client.get("/api/v1/lobby/summary")
    assert r.status_code == 200
    body = r.json()
    assert "podium" in body and "daily" in body and "me" in body
```

- [ ] **Step 2: 注册路由**

```python
from app import lobby as lobby_mod

@app.get("/api/v1/lobby/summary")
async def lobby_summary(x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id")):
    tid = (x_terminal_id or "").strip() or None
    return lobby_mod.get_lobby_summary(tid)
```

- [ ] **Step 3: `pytest tests/test_lobby_summary.py -v` → PASS**

- [ ] **Step 4: Commit** `feat(api): expose GET /api/v1/lobby/summary`

---

### Task 3: 主题竞技组件 CSS

**Files:**
- Modify: `web/css/fgb-theme.css`

**Interfaces:**
- Produces: 下列类可供壳页使用（名称固定）

- [ ] **Step 1: 追加样式**（接在文件后部）

```css
.fgb-stat-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: .65rem;
  margin: 0 0 1rem;
}
.fgb-stat-strip .cell {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: .75rem .85rem;
}
.fgb-stat-strip .label { color: var(--muted); font-size: .78rem; }
.fgb-stat-strip .value { font-weight: 700; font-size: 1.05rem; margin-top: .25rem; }

.fgb-arena-split {
  display: grid;
  grid-template-columns: 1.15fr .85fr;
  gap: .85rem;
  margin-bottom: 1.25rem;
}
@media (max-width: 720px) {
  .fgb-arena-split { grid-template-columns: 1fr; }
  .fgb-stat-strip { grid-template-columns: 1fr; }
}

.fgb-cta-daily {
  display: inline-block;
  margin-top: .65rem;
  border: 0;
  border-radius: 12px;
  padding: .7rem 1.1rem;
  font: inherit;
  font-weight: 700;
  color: #062016;
  background: linear-gradient(160deg, var(--accent), var(--accent-deep));
  text-decoration: none;
  cursor: pointer;
}

.fgb-podium {
  display: grid;
  grid-template-columns: 1fr 1.15fr 1fr;
  gap: .5rem;
  align-items: end;
  margin: 0 0 1rem;
}
.fgb-podium .spot {
  text-align: center;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: .75rem .5rem;
  background: rgba(255,255,255,.03);
}
.fgb-podium-1 { border-color: rgba(212,168,75,.55); min-height: 7rem; }
.fgb-podium-2 { border-color: rgba(168,180,188,.45); min-height: 5.5rem; }
.fgb-podium-3 { border-color: rgba(196,122,74,.45); min-height: 5rem; }

.fgb-game-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: .75rem;
  padding: .85rem 1rem;
  margin-bottom: .55rem;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
  text-decoration: none;
  color: inherit;
}
.fgb-game-row:hover { border-color: rgba(62,207,142,.4); }
.fgb-game-row .meta { color: var(--muted); font-size: .85rem; }
.fgb-game-row.is-muted { opacity: .72; }
```

- [ ] **Step 2: Commit** `feat(theme): add arena components to fgb-theme.css`

---

### Task 4: `FGB.loadLobbySummary`

**Files:**
- Modify: `web/js/fgb-client.js`

**Interfaces:**
- Produces: `FGB.loadLobbySummary()` → `Promise<object|null>`（失败返回 `null`，不抛）

- [ ] **Step 1: 实现**

```javascript
function loadLobbySummary() {
  return api("/api/v1/lobby/summary").catch(function () { return null; });
}
// 挂到 global.FGB
```

`api()` 已自动带 `X-Terminal-Id`（确认现有实现；若未带，与 `me()` 相同方式加 header）。

- [ ] **Step 2: Commit** `feat(client): add loadLobbySummary`

---

### Task 5: 重建大厅 `web/index.html`

**Files:**
- Modify: `web/index.html`

**Interfaces:**
- Consumes: `FGB.loadLobbySummary`、`FGB.ensureRegistered`、主题类

- [ ] **Step 1: 替换 main 结构**（保留注册 modal）

结构骨架：

```html
<main class="fgb-shell">
  <header class="fgb-topbar">...</header>
  <section class="fgb-stat-strip" id="stat-strip">
    <div class="cell"><div class="label">今日挑战名次</div><div class="value" id="stat-rank">—</div></div>
    <div class="cell"><div class="label">与第 1 名</div><div class="value" id="stat-gap">—</div></div>
    <div class="cell"><div class="label">最近一局</div><div class="value" id="stat-recent">—</div></div>
  </section>
  <section class="fgb-arena-split">
    <a class="fgb-card fgb-card-daily" href="/daily" id="daily-card">
      <div class="tag">今日对决</div>
      <h2>每日挑战</h2>
      <p id="daily-progress">加载中…</p>
      <span class="fgb-cta-daily" id="daily-cta">开始挑战</span>
    </a>
    <div class="fgb-panel fgb-panel-pad">
      <h3 class="fgb-page-kicker">今日挑战榜</h3>
      <ol id="podium-list"></ol>
      <a class="fgb-nav-link" href="/daily/leaderboard">完整榜 →</a>
    </div>
  </section>
  <h2 class="fgb-page-title">自由训练</h2>
  <div id="game-list"><!-- fgb-game-row 链接，解法库加 is-muted --></div>
  <p class="fgb-footer-link"><a href="/admin">管理</a></p>
</main>
```

- [ ] **Step 2: JS 绑定**

```javascript
function renderSummary(s) {
  if (!s) return;
  var me = s.me || {};
  document.getElementById("stat-rank").textContent = me.dailyRank ? ("#" + me.dailyRank) : "未上榜";
  document.getElementById("stat-gap").textContent = me.gapLabel || "—";
  var recent = s.recent;
  document.getElementById("stat-recent").textContent = recent
    ? ((recent.gameTitle || "") + " · " + (recent.display || ""))
    : "暂无";
  document.getElementById("daily-progress").textContent = (s.daily && s.daily.myProgressLabel) || "—";
  var cta = document.getElementById("daily-cta");
  var c = (s.daily && s.daily.cta) || "start";
  cta.textContent = c === "view" ? "查看挑战" : (c === "continue" ? "继续挑战" : "开始挑战");
  var ol = document.getElementById("podium-list");
  ol.innerHTML = "";
  (s.podium || []).forEach(function (p) {
    var li = document.createElement("li");
    li.textContent = p.rank + ". " + p.nickname + " · " + (p.display || "");
    ol.appendChild(li);
  });
  if (!(s.podium || []).length) {
    ol.innerHTML = "<li class=\"fgb-empty\">还没有成绩，去做每日挑战吧</li>";
  }
}
FGB.loadLobbySummary().then(renderSummary);
```

注册成功后再次 `loadLobbySummary`。

- [ ] **Step 3: 浏览器手测**（本地起服务）大厅分区与 summary 占位

- [ ] **Step 4: Commit** `feat(lobby): rebuild index as season dashboard`

---

### Task 6: 两榜领奖台

**Files:**
- Modify: `web/leaderboard.html`
- Modify: `web/daily-leaderboard.html`

**Interfaces:**
- Consumes: 现有 leaderboard API；主题 `.fgb-podium*`

- [ ] **Step 1: 游戏榜**  
渲染列表前，若 `items.length`：取前三填入 podium（名次 2-1-3 视觉顺序可选：左银中金右铜），第 4 名起进表格；本人行保留 `fgb-row-me`。空态用 `.fgb-empty` + 链到 `/`。

- [ ] **Step 2: 挑战榜**  
同样领奖台；顶栏链「回大厅」「游戏榜」。

- [ ] **Step 3: Commit** `feat(boards): podium layout for game and daily leaderboards`

---

### Task 7: 每日壳竞技化

**Files:**
- Modify: `web/daily.html`

**Interfaces:**
- Consumes: `FGB.loadLobbySummary`（准备页 podium）；既有 daily run API **行为不变**

- [ ] **Step 1: 准备页**  
在关卡列表旁（或下方）加 `#prep-podium`，`loadLobbySummary` 填前三；主按钮保留 `btn-start`。

- [ ] **Step 2: 结算页**  
标题下加大号总用时；可选显示 summary 的 `me.dailyRank`（结算后重新拉 summary）。不改 iframe / postMessage。

- [ ] **Step 3: Commit** `feat(daily): arena styling for prep and result panels`

---

### Task 8: 验收

**Files:** 无强制新文件

- [ ] **Step 1:** `pytest -q` → 全绿  
- [ ] **Step 2:** 手测 checklist（spec §10）  
  - 大厅四区清晰  
  - 无终端 / 无成绩不崩  
  - 窄屏堆叠  
  - 每日闯关全流程  
  - `/css/fgb-theme.css` 与 `/api/v1/lobby/summary` 200  
- [ ] **Step 3:** 若有修复则提交；推送仅在用户要求时执行

---

## Plan self-review

1. **Spec 覆盖：** summary API、战绩条、赛季分栏、列表游戏、两榜领奖台、每日准备/结算、主题类、测试与验收 — 均有 Task；游戏首页明确不在任务中。  
2. **无占位：** 无 TBD；cta/gap 规则已写死。  
3. **命名一致：** `get_lobby_summary` / `loadLobbySummary` / 响应字段与 spec §5.2 对齐。

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-01-lobby-arena.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每 Task 新开子代理，任务间复查  
2. **Inline Execution** — 本会话按计划连续执行并设检查点  

Which approach?
