# 每日挑战（串联闯关）设计

**日期:** 2026-08-31  
**状态:** 已确认  
**范围:** 大厅每日挑战入口、串联闯关壳、管理员模板/重生成、题面 seed 锁定、每日挑战榜、管理员密码入口

---

## 1. 目标

在家庭游戏盒大厅增加 **每日挑战**：按管理员模板把多款游戏串成一条闯关；当天题面与参数固定；玩家分关计时 + 总计时；退出也记成绩；每次开挑战为新记录；独立挑战排行榜。

管理员可配置参与游戏种类、每关难度、顺序；仅管理员可重生成；旧组合保留最近 20 条；首次进入管理页设置密码。

## 2. 非目标

- 改管理员密码 / 多管理员账号
- 每日挑战成就徽章
- 服务端预生成完整题面 JSON（本期用 per-stage seed）
- 关内暂停总计时
- 把每日成绩写入现有单游戏 `/api/v1/scores` 榜

## 3. 已确认产品决策

| 项 | 决策 |
|----|------|
| 玩法 | 串联闯关（按顺序一关接一关） |
| 计时 | 每关独立计时 + 闯关总计时（含关间） |
| 退出 | 记录当前进度与总用时；下次开始 = 新 run |
| 排行 | 独立「每日挑战榜」：通关优先 → 完成关数降序 → 总用时升序 |
| 生成 | 按管理员模板，当天首次访问自动生成；管理员可手动重生成 |
| 重生成与成绩 | 旧组合归档；**当日挑战榜记录不清空** |
| 题面 | 锁定种类 / 难度 / 顺序 + **seed 锁定题面**（同日同关所有人同一套题） |
| 实现路径 | 服务端组合 + 统一 seed + 轻量闯关壳（iframe + postMessage） |

## 4. 架构

```
浏览器
  ├── /                 大厅（每日挑战卡 + 管理入口）
  ├── /daily            闯关壳（计时、串联、结算）
  ├── /daily/leaderboard
  ├── /admin            设密 / 登录 / 模板 / 重生成 / 历史
  └── /games/...        各游戏（?daily=1&tier=&seed=&runId=）

FastAPI
  ├── GET  /api/v1/daily/today
  ├── POST /api/v1/daily/runs
  ├── PATCH /api/v1/daily/runs/{runId}
  ├── GET  /api/v1/daily/leaderboard
  └── /api/v1/admin/*   密码、模板、重生成、历史

data/
  ├── daily_admin.json
  ├── daily_challenges.json
  └── daily_runs.json
```

时区：服务端用**本机本地日历日** `YYYY-MM-DD` 判断「今天」。

可玩游戏（默认可入模板，不含解法库）：  
`24points`、`schulte`、`stroop`、`cancel`、`simon`、`spot-diff`、`maze`、`sudoku`。

难度档位与现网一致：`intro` / `simple` / `normal` / `hard` / `master` / `god`。

---

## 5. 数据模型

### 5.1 `data/daily_admin.json`

| 字段 | 说明 |
|------|------|
| `passwordHash` | 空 = 尚未设密 |
| `salt` | 随机盐；`hash = sha256(salt + password)` |
| `sessionToken` | 登录后令牌 |
| `sessionExpiresAt` | 约 12 小时 |
| `template.stages[]` | `{ gameId, tier }`，有序；默认全部可玩游戏、`tier=normal` |

### 5.2 `data/daily_challenges.json`

| 字段 | 说明 |
|------|------|
| `current` | 当前生效组合，或 `null` |
| `history[]` | 最近 20 条旧组合（超出丢弃最旧） |

**组合 `combo`：**

```text
comboId, date, createdAt, source (auto|admin)
stages: [{ gameId, title, tier, tierLabel, seed }]
```

- 每关独立随机 `seed`（整数），保证同日同关题面一致。
- 跨日：访问时若 `current.date != 今天`，将 `current` 压入 `history`，再按模板自动生成新组合。
- 管理员重生成：归档当前 → 按**当前模板**生成新 `current`（`source=admin`）；**不删除** `daily_runs`。

### 5.3 `data/daily_runs.json`

每次「开始挑战」新建一条：

```text
runId, comboId, date, terminalId, nickname
status: running | exited | finished
startedAt, endedAt
totalTimeMs
stagesDone
stageResults[]: { gameId, tier, timeMs, completed }
```

排行（指定 `date`，默认今天）：  
`finished` 优先 → `stagesDone` 降序 → `totalTimeMs` 升序。  
同一终端可有多条（每次挑战新记录）。重生成后新旧 `comboId` 的成绩同日同榜并存。

---

## 6. API 与权限

管理员鉴权：请求头 `X-Admin-Token`（前端存 `sessionStorage`）。

### 6.1 玩家

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/daily/today` | 取当日组合；无或过期则按模板自动生成 |
| `POST` | `/api/v1/daily/runs` | 开始挑战（需已注册 `X-Terminal-Id`）→ `runId` + 关卡 |
| `PATCH` | `/api/v1/daily/runs/{runId}` | 完成一关 / 退出 / 通关 |
| `GET` | `/api/v1/daily/leaderboard?date=` | 挑战榜，默认今天 |

`GET /today` 可不登录预览关卡；写 run 必须已注册。

### 6.2 管理员

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/admin/status` | `{ hasPassword, authenticated }` |
| `POST` | `/api/v1/admin/setup` | 仅未设密时设初始密码 → token |
| `POST` | `/api/v1/admin/login` | 登录 → token |
| `POST` | `/api/v1/admin/logout` | 清 session |
| `GET/PUT` | `/api/v1/admin/daily/template` | 读/写模板（保存不触发重生成） |
| `POST` | `/api/v1/admin/daily/regenerate` | 归档并生成新组合；不删 runs |
| `GET` | `/api/v1/admin/daily/history` | 最近 20 条摘要 |

错误密码 / 无效 token → `401`。本期无改密接口。

### 6.3 页面路由

| 路径 | 页面 |
|------|------|
| `/` | 大厅：每日挑战卡 + 低调管理入口 |
| `/daily` | 闯关壳 |
| `/daily/leaderboard` | 每日挑战榜 |
| `/admin` | 管理页 |

---

## 7. 玩家闯关体验

### 7.1 大厅

- 「每日挑战」卡片（略突出）；未注册时与其他游戏一同锁定。
- 链到 `/daily/leaderboard`；「管理」放页脚小字。

### 7.2 `/daily` 壳

1. **准备页**：今日关卡列表（名 + 难度）→「开始挑战」。
2. **开始**：`POST /runs`，启动总计时，进入第 1 关。
3. **关内顶栏**：第 i/N · 本关用时 · 总计时 ·「退出」。
4. **加载**：同页 `iframe`，URL 形如  
   `/games/.../...?daily=1&runId=...&tier=...&seed=...&stageIndex=...`
5. **通关一关**：游戏 `postMessage`  
   `{ type: "fgb-daily-stage-done", timeMs }`  
   → 壳 `PATCH` → 自动下一关。
6. **全部完成**：`status=finished`，结算页（总用时 / 各关用时），可再开（新 run）或看榜。
7. **退出**：确认后 `status=exited`；已完成关写入；当前未完成关 `completed=false`。
8. **计时**：总计时自「开始」连续走（含关间）；本关用时自进入该关算到 `stage-done`。

游戏内认输/放弃本关 → 视为退出结算，不跳下一关。  
iframe 加载失败：提示重试，总计时不暂停。

### 7.3 挑战榜页

昵称、状态（通关/退出）、完成关数、总用时、各关摘要；默认今天。

---

## 8. 管理员页

1. 首次：设置密码（两次确认）→ 自动登录。
2. 之后：密码登录；token 过期回登录。
3. **模板**：勾选游戏、每关难度、调顺序；保存只改模板。
4. **今日组合**：展示当前组合；「重新生成今日挑战」（二次确认）。
5. **历史**：最近 20 条只读摘要。
6. 回大厅链接。

---

## 9. 各游戏适配

共享脚本 `web/js/fgb-daily.js`：

| 项 | 行为 |
|----|------|
| 检测 | URL 含 `daily=1` |
| 启动 | 跳过自选难度；用 `tier` + `seed` 直接开 **单局**（不走各游戏自带多题挑战模式） |
| RNG | mulberry32(seed) 替换本局 `Math.random` / `randInt` |
| 完成 | `parent.postMessage({ type: "fgb-daily-stage-done", timeMs }, ...)` |
| 计分 | **不**调用普通 `/api/v1/scores` |
| UI | 隐藏会破坏串联的「回游戏首页」等；或改为通知壳退出 |

覆盖 8 款可玩游戏页面（含 `24points/play.html`）。

---

## 10. 错误与边界

- 模板为空：禁止保存；若库内损坏导致空模板，自动生成失败并返回明确错误。
- 未知 `gameId` / 非法 `tier`：拒绝写入模板。
- `PATCH` 非本人 run 或非 `running`：`400/403`。
- 管理员未登录调用 regenerate / 写模板：`401`。
- 本地日切：以服务端本地日为准，不依赖客户端时钟做生成判定。

---

## 11. 测试要点

- 首次访问自动生成；同日再次访问 `comboId`/`seed` 不变。
- 改模板不改今日组合，直到 regenerate 或跨日。
- 重生成后 history ≤ 20；当日 runs 仍在榜。
- 通关 / 中途退出 / 再开新 run 各写一条；榜排序正确。
- 设密 → 登录 → 改模板 → 重生成 全流程。
- 每日模式下各游戏同 seed 两次进入题面一致；不向普通 scores 提交。
