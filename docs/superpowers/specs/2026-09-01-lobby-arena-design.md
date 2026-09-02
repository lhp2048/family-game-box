# 家庭竞技厅壳层重设计

**日期:** 2026-09-01  
**状态:** 已确认  
**产品:** family_game_box  
**前置:** 主题换皮（`fgb-theme.css`）已落地；本期在其上做**信息架构重设计**，而非再次换色。

---

## 1. 目标

把大厅、游戏排行、挑战排行、每日挑战壳做成「家庭竞技厅」：

- 打开大厅即看到**我的战况**、**今日挑战**、**今日榜**
- 自由游戏退到列表区
- 两榜与每日壳同一套竞技语言（领奖台、本人高亮、强 CTA）

## 2. 已确认决策

| 项 | 决策 |
|----|------|
| 气质 | 竞技厅风（在现有深炭绿令牌上强化榜与挑战） |
| 大厅布局 | **C 赛季看板**：顶战绩条 → 中分栏（挑战 + 榜）→ 列表式游戏 |
| 战绩条 | **B 家庭对比**：我的名次 + 与第 1 差距 + 最近一局 |
| 页面范围 | 大厅 + 两榜 + 每日壳；**各游戏首页本期不动** |
| 数据 | 新增 **`GET /api/v1/lobby/summary`** |
| 实现路径 | 壳页 DOM 重建 + 扩展主题组件 + 汇总 API |

## 3. 非目标

- 各游戏首页 / 对局 UI 重设计
- 成就、连胜、赛季结算等新玩法
- Admin 信息架构大改（可仅跟主题色）
- 新插画资源包
- 修改计分 / 排行排序规则 / 每日闯关 iframe 协议

## 4. 大厅信息架构

自上而下：

1. **顶栏**：品牌「家庭游戏盒」· 昵称 chip · 挑战榜 · 排行榜  
2. **战绩条**（三格）  
   - 我的今日挑战名次；未上榜文案「未上榜」  
   - 与第 1 名差距：双方均 `finished` → 用时差（如 `落后 31s` / `领先`）；否则关数差或「—」  
   - 最近一局：`gameTitle` + `display`（本 terminal 最近一条成绩）  
3. **中分栏**（`min-width` 合适时左右；窄屏上下堆叠）  
   - 左：每日挑战主卡（关数、进度摘要、CTA：`开始` / `继续`）  
   - 右：今日挑战榜前三（金/银/铜）+ 链到完整挑战榜  
4. **自由训练**：列表行（标题 · 短说明 · 进入）；24 点解法库置底、弱样式  
5. **页脚**：小号「管理」

宽屏参考原型：`.superpowers/brainstorm/lobby-arena-mockups/dual-core-layouts.html` 方案 C。

## 5. API：`GET /api/v1/lobby/summary`

### 5.1 请求

- Header：`X-Terminal-Id`（可选；无则个人字段为空，仍返回 podium / 公共部分）
- 无 query；日期固定「本地今日」（与 daily 一致）

### 5.2 响应

```text
date: YYYY-MM-DD
me: {
  nickname: string | null
  dailyRank: number | null          # 1-based；未上榜 null
  dailyStatus: unfinished|finished|running|absent | null
  stagesDone: number
  stageCount: number
  gapToFirstMs: number | null       # 仅双方 finished 时有意义；我方减第1（正=更慢）
  gapLabel: string                  # 展示用短文案
}
podium: [{
  rank, nickname, status, stagesDone, totalTimeMs, display
}]                                 # 最多 3；排序规则同现有挑战榜
daily: {
  stageCount: number
  myProgressLabel: string           # 如「未开始」「进行中 2/4」「已通关」
  cta: "start" | "continue" | "view"
}
recent: {
  gameId, gameTitle, display, playedAt
} | null
```

### 5.3 服务端拼装来源

- 今日挑战榜 / 本 terminal 今日 run：`daily_runs`（与 `/api/v1/daily/leaderboard`、`/api/v1/daily/today` 同源逻辑）
- 最近一局：scores 存储中该 `terminalId` 最新一条（可复用 recent 全局列表过滤，或直接扫 entries）
- **不**改变既有榜排序键：通关优先 → 完成关数降序 → 总用时升序

### 5.4 前端

- `FGB.loadLobbySummary()` 封装；大厅首屏调用
- 失败：战绩条/ podium 显示空态，不阻塞游戏列表渲染

## 6. 两榜页

| 页 | 改动 |
|----|------|
| `web/leaderboard.html` | 顶栏统一；前三 **领奖台**；其余表/列表；本人行高亮；Tab 改竞技胶囊；排序逻辑不变 |
| `web/daily-leaderboard.html` | 同上语言；链回大厅与游戏榜 |

空态：居中文案 + CTA（去挑战 / 去玩一局）。

## 7. 每日挑战壳（`web/daily.html`）

| 状态 | UI |
|------|-----|
| 准备 | 关卡列表 + 主 CTA；旁侧或下方「今日榜前三」摘要 |
| 对局 | HUD（关序、双计时、退出）视觉跟竞技厅；**iframe / postMessage 不变** |
| 结算 | 总用时/完成关数突出；「再来一次 / 看挑战榜 / 回大厅」；若 summary 或榜可算则显示粗排名 |

## 8. 主题扩展

在 `web/css/fgb-theme.css` 增加组件类（名称可微调，语义固定）：

- `.fgb-stat-strip` — 战绩条  
- `.fgb-podium` / `.fgb-podium-1|2|3` — 领奖台  
- `.fgb-arena-split` — 中分栏  
- `.fgb-game-row` — 列表式游戏行  
- `.fgb-cta-daily` — 挑战主按钮  

令牌沿用现有：`--ink --muted --accent --panel --line --gold/--silver/--bronze --warn` 等。禁止紫粉霓虹、奶油纸、报纸风。

## 9. 文件与测试

| 文件 | 职责 |
|------|------|
| `app/lobby.py`（或等价） | summary 拼装 |
| `app/main.py` | 注册路由 |
| `web/js/fgb-client.js` | `loadLobbySummary` |
| `web/index.html` | 赛季看板 DOM + 绑定 |
| `web/leaderboard.html` / `daily-leaderboard.html` / `daily.html` | 竞技厅结构 |
| `web/css/fgb-theme.css` | 新组件 |
| `tests/test_lobby_summary.py` | summary 字段与排序/空态 |

构建：已有 `web/css` 复制与 `/css` mount，无需新静态挂载。

## 10. 验收

1. 大厅分区清晰：战绩 / 挑战 / 榜 / 训练列表  
2. 无终端、无成绩、无今日榜时不崩，有占位与引导  
3. 窄屏中分栏上下堆叠可读  
4. 每日闯关开始→完成→退出与改前行为一致  
5. `pytest` 全绿；`GET /css/fgb-theme.css` 与 `GET /api/v1/lobby/summary` 可用  

## 11. 分支

建议在 `feature/lobby-theme` 上继续，或开 `feature/lobby-arena`；勿混入无关 `family-product.json` 版本噪声除非打包需要。
