# 游戏大厅统一主题 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用共享 `fgb-theme.css` 把大厅、排行、挑战壳与各游戏首页/选难度统一成轻竞技大厅观感；对局区仅轻贴皮。

**Architecture:** 单一主题 CSS 定义令牌与通用组件类；壳页 `<link>` 引用并改用主题 class；`game_common.build_page` / `inject_standalone_overlays` 注入主题链接并覆盖 `:root` 为深色大厅令牌；生成后刷新 `web/games/**`；构建复制 `web/css/`。

**Tech Stack:** 静态 HTML/CSS/JS；Python 游戏页生成器；无新后端 API。

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-01-lobby-theme-design.md`
- 范围 B：壳页 + 游戏首页/选难度；对局布局/玩法不变
- 气质：深炭绿背景 + 青绿强调；禁止紫粉、奶油纸、报纸风、过亮霓虹
- 不改 API / 难度配置 / 成绩逻辑
- 提交在 `feature/lobby-theme`；勿混入无关 `family-product.json` 除非版本 bump 需要
- 改游戏生成器后必须重新跑各 `generate*.py` / `schulte/build_page.py`

## File map

| 文件 | 职责 |
|------|------|
| `web/css/fgb-theme.css` | 令牌 + 顶栏/卡片/按钮/榜/徽章/空态 |
| `web/js/fgb-shell.js` | 可选：根据 `data-fgb-page` 补齐顶栏右侧链接一致性（若各页手写结构一致可极简） |
| `web/index.html` 等壳页 | link 主题 + 结构 class |
| `games/common/game_common.py` | 注入 theme link；COMMON_CSS `:root` 对齐深色令牌 |
| `games/schulte/index.html` + `build_page.py` | link 主题 |
| `games/24points/generate_play.py` | link 主题；解法库轻贴皮 |
| `scripts/build.bat` | 复制 `web/css` |

---

### Task 1: 主题 CSS 骨架

**Files:**
- Create: `web/css/fgb-theme.css`
- Modify: `scripts/build.bat`（在 `xcopy web\js` 附近增加 css 复制）

**Interfaces:**
- Produces: CSS 变量与类名（后续任务只使用这些名字）
  - 变量：`--ink --muted --accent --accent-deep --panel --line --warn --danger --gold --silver --bronze --shadow --display --sans --paper`
  - 类：`.fgb-shell` `.fgb-topbar` `.fgb-brand` `.fgb-nav` `.fgb-chip` `.fgb-btn` `.fgb-btn-ghost` `.fgb-card` `.fgb-card-daily` `.fgb-grid` `.fgb-lead` `.fgb-panel` `.fgb-tabs` `.fgb-tab` `.fgb-tab.is-active` `.fgb-table` `.fgb-rank` `.fgb-rank-1|2|3` `.fgb-row-me` `.fgb-empty` `.fgb-page-title`

- [ ] **Step 1: 创建 `web/css/fgb-theme.css`**

写入完整令牌与组件（深炭绿底、近白字、青绿强调）。至少包含：

```css
@import url("https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap");

:root {
  --ink: #e8f2ec;
  --muted: #8fa399;
  --accent: #3ecf8e;
  --accent-deep: #1a9f68;
  --panel: rgba(18, 32, 28, 0.82);
  --line: rgba(232, 242, 236, 0.12);
  --warn: #e8a04a;
  --danger: #e07060;
  --gold: #d4a84b;
  --silver: #a8b4bc;
  --bronze: #c47a4a;
  --shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
  --display: "Fraunces", "Songti SC", serif;
  --sans: "DM Sans", "PingFang SC", "Microsoft YaHei UI", sans-serif;
  --paper: #0c1411;
}

html, body {
  margin: 0;
  min-height: 100%;
  font-family: var(--sans);
  color: var(--ink);
  background:
    radial-gradient(900px 480px at 12% -8%, rgba(62, 207, 142, 0.18), transparent 55%),
    radial-gradient(700px 400px at 100% 0%, rgba(232, 160, 74, 0.08), transparent 50%),
    linear-gradient(165deg, #0a1210 0%, #0c1411 45%, #101a16 100%);
}

/* … topbar / card / btn / tabs / table / rank badges / empty … */
```

Google Fonts 若内网不可用：保留本地 fallback（思源/雅黑），勿阻塞页面。

- [ ] **Step 2: `scripts/build.bat` 增加**

在 js 复制附近：

```bat
if not exist "dist\web\css" mkdir "dist\web\css"
xcopy /Y "web\css\*" "dist\web\css\" >nul 2>nul
```

- [ ] **Step 3: Commit** `feat(theme): add fgb-theme.css and pack css in build`

---

### Task 2: 大厅页

**Files:**
- Modify: `web/index.html`

**Interfaces:**
- Consumes: Task 1 类名
- Produces: 大厅 DOM 使用 `.fgb-*`；注册弹窗跟深色 panel

- [ ] **Step 1: `<head>` 增加**

```html
<link rel="stylesheet" href="/css/fgb-theme.css">
```

精简/替换页内冲突的浅色 `:root` 与 body 背景（保留仅本页特有的少量规则，或改为主题变量）。

- [ ] **Step 2: 顶栏与网格**

- 顶栏：`.fgb-topbar` — 左 `.fgb-brand`「家庭游戏盒」，右昵称 `.fgb-chip` + `.fgb-nav` 链到 `/daily/leaderboard`、`/leaderboard`
- 标题用 `font-family: var(--display)`
- 每日挑战卡：`.fgb-card.fgb-card-daily` + 「今日」徽章
- 游戏卡：`.fgb-card`；悬停上移
- 注册 modal：深色 panel + accent 主按钮

- [ ] **Step 3: 浏览器打开 `/` 目测：深色大厅、卡片可读、未登录锁卡仍有效**

- [ ] **Step 4: Commit** `feat(lobby): restyle index with shared theme`

---

### Task 3: 游戏排行 + 挑战排行

**Files:**
- Modify: `web/leaderboard.html`
- Modify: `web/daily-leaderboard.html`

**Interfaces:**
- Consumes: `.fgb-rank-1|2|3` `.fgb-row-me` `.fgb-tabs` `.fgb-tab`
- Produces: 渲染行时为 rank 1–3 加徽章 class；本人行加 `.fgb-row-me`（挑战榜用 `X-Terminal-Id` 或现有 nickname 匹配若无 terminalId 则仅样式表就绪）

- [ ] **Step 1: 两页 link 主题；顶栏与大厅一致（含回大厅）**

- [ ] **Step 2: `leaderboard.html`**

- Tab 用 `.fgb-tab` / `.is-active`
- 表格包在 `.fgb-panel`；表头/单元格跟 `--line`
- `renderRecentRows` / `renderSimpleRows`：若 `item.rank===1|2|3`，rank 单元格加 `fgb-rank fgb-rank-N`；`item.terminalId === myTerminal` 时 `tr` 加 `fgb-row-me`

- [ ] **Step 3: `daily-leaderboard.html`**

- 同 panel/table 样式
- 若 API 项含 `terminalId`，本人高亮；否则至少前三徽章（按行序 1–3）

- [ ] **Step 4: 手测两榜 + Commit** `feat(leaderboard): apply lobby theme and rank badges`

---

### Task 4: 每日挑战壳 + 管理页

**Files:**
- Modify: `web/daily.html`
- Modify: `web/admin.html`

- [ ] **Step 1: `daily.html` link 主题；准备/结算用 `.fgb-panel`；HUD 用 panel；iframe `.frame-wrap` 圆角 + `--line`；按钮 `.fgb-btn`**

- [ ] **Step 2: `admin.html` link 主题；背景/卡片/输入框/按钮跟令牌（功能与页签逻辑不变）**

- [ ] **Step 3: Commit** `feat(shell): theme daily challenge and admin pages`

---

### Task 5: 游戏页接入主题（common + 生成）

**Files:**
- Modify: `games/common/game_common.py`（`COMMON_CSS` `:root` 与 `body` 背景对齐主题；`build_page` head 增加 `<link rel="stylesheet" href="/css/fgb-theme.css">`；`inject_standalone_overlays` 同样在 `</head>` 前插入 link）
- Modify: `games/schulte/index.html`（head link）
- Modify: `games/24points/generate_play.py`（play + library 轻贴皮：link + 顶栏回大厅）
- Regenerate: 全部游戏 HTML

**Interfaces:**
- Consumes: `/css/fgb-theme.css`
- Produces: 生成页含 theme link；首页 `mode-btn` / `choice-row` 在深色底可读（COMMON_CSS 内按钮色改为用 var）

- [ ] **Step 1: 更新 `COMMON_CSS` 的 `:root` 与 `body` 为深色令牌（与 fgb-theme 一致），避免双主题打架**

- [ ] **Step 2: `build_page` / `inject_standalone_overlays` 注入**

```html
<link rel="stylesheet" href="/css/fgb-theme.css">
```

放在 `<title>` 后、DAILY_HEAD 前。

- [ ] **Step 3: 舒尔特源码 + 24 点 play/library 同样 link；首页「返回大厅」可用 `.fgb-nav` 样式**

- [ ] **Step 4: 重新生成**

```powershell
python games\schulte\build_page.py
foreach ($g in stroop,cancel,simon,spot_diff,maze,sudoku) { python games\$g\generate.py }
python games\24points\generate_play.py
# library 若单独脚本则一并执行
```

- [ ] **Step 5: 抽查 stroop / 24points / schulte：首页深色、对局可玩、回大厅正常**

- [ ] **Step 6: Commit** `feat(games): wire shared lobby theme into generated game pages`

---

### Task 6: 验收与收尾

- [ ] **Step 1: `pytest -q` 全绿（主题无后端破坏）**

- [ ] **Step 2: Spec §6 清单勾选（大厅连续、两榜徽章、对比度、玩法无回归）**

- [ ] **Step 3: 推送 `feature/lobby-theme`（若用户要求）**

---

## Plan self-review

1. Spec 覆盖：主题 CSS、大厅、两榜、daily、admin、游戏首页、对局轻贴皮、解法库轻贴皮、build 复制 css — 均有 Task  
2. 无 TBD  
3. 类名在 Task 1 定义，后续任务复用一致  

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-01-lobby-theme.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每 Task 新开子代理，任务间复查  
2. **Inline Execution** — 本会话按计划连续执行并设检查点  

Which approach?
