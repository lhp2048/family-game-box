# 全局难度参数配置设计

**日期:** 2026-09-01  
**状态:** 已确认  
**范围:** 管理端编辑各游戏六档难度参数；大厅单机与每日挑战共用；含 24 点数字范围硬过滤与分位 cuts

---

## 1. 目标

将各游戏写死在前端的 `DIFF` / `TIERS` 提升为**可配置的全局难度表**：

- 管理员在 `/admin` 编辑每款游戏、每一档的具体参数
- **立刻对之后新开的对局生效**（大厅 + 每日挑战开局拉取）
- 进行中的对局不改；每游戏可一键恢复出厂默认
- 24 点支持每档 `minNum`/`maxNum` 硬过滤，以及全局 `cuts` 分位

## 2. 非目标

- 改参后自动清空或迁移排行榜
- 按玩家个性化难度
- 管理页内嵌试玩预览
- 构建期 regenerate 静态 HTML 写死参数

## 3. 已确认决策

| 项 | 决策 |
|----|------|
| 作用范围 | **全局**（大厅单机与每日挑战同一套表） |
| 生效时机 | 保存后**新开局**立即用新参；进行中不改 |
| 24 点 | 可改 `cuts` + 每档 `minNum`/`maxNum`/`label`/`desc`；数字范围 **硬过滤** |
| 恢复默认 | 支持**按游戏**恢复出厂默认（亦可整表恢复） |
| 实现路径 | 服务端 JSON 难度表 + 游戏启动时 fetch 合并 |

---

## 4. 数据模型

文件：`data/difficulty.json`（经 `app/storage.py`）。

```text
version: 1
updatedAt: ISO-8601
games: {
  <gameId>: {
    # 多数游戏：
    tiers: {
      intro|simple|normal|hard|master|god: { ...params, label }
    }
    # 24points 额外：
    cuts: [number × 6]   # 累计上界，末项 ≥ 1.0
  }
}
```

### 4.1 各游戏字段

| 游戏 | 每档字段 | 校验 |
|------|----------|------|
| schulte | `size`, `reverse`, `label` | `size∈{3,4,5,6}`；`reverse` 布尔 |
| sudoku | `size`, `givens`, `label` | `size∈{4,6,9}`；`1≤givens≤size²-1` |
| stroop | `trialLimit`, `timeLimitMs`, `congruentRate`, `label` | 限次/限时至少一个 >0；`congruentRate∈[0,1]` |
| cancel | `size`, `pct`, `label` | `size` 偶数 8–20；`pct∈(0,0.5)` |
| simon | `trials`, `label` | `trials∈[5,100]` |
| spot-diff | `n`, `diffs`, `label` | `n∈[4,12]`；`1≤diffs≤n²/2` |
| maze | `size`, `label` | `size` 奇数 5–31 |
| 24points | 全局 `cuts[6]`；每档 `minNum`,`maxNum`,`label`,`desc` | 见 §4.2 |

服务端内置 **defaults**（与当前代码硬编码一致）。磁盘文件可为部分覆盖；`GET` 返回 **defaults ⊕ overrides** 完整表。

### 4.2 24 点

- **开局划档**：对 bank 题目按既有 hardness 排序，用**当前** `cuts` 重新划档（改 cuts 立即生效，不必重建 `bank.json`）。
- **硬过滤**：选中档后，仅保留四数均满足 `minNum ≤ x ≤ maxNum` 的题。
- **空池回退**：同范围换相邻档 → 再放宽范围一步 → 仍空则提示「该档无题，请调大数字范围」。
- **`cuts`**：长度 6、单调非降、末项 ≥ 1.0。

### 4.3 与每日挑战的关系

- 每日组合仍存 `tier`（档名）；开局各游戏拉取**最新全局表**应用该档参数。
- 已生成组合不回溯改历史记录；同日未 regenerate 时，后开的每日关也会读到新表。
- 排行榜键仍为 `gameId+mode+tier`；改参不改档 id。

---

## 5. API

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| `GET` | `/api/v1/difficulty` | 无 | 合并后完整表；可选 `?gameId=` |
| `GET` | `/api/v1/difficulty/defaults` | 无或管理员 | 出厂默认 |
| `PUT` | `/api/v1/admin/difficulty` | `X-Admin-Token` | 写入覆盖（整表或 `games` 子集）；校验失败 400 |
| `POST` | `/api/v1/admin/difficulty/reset` | 同上 | body `{ "gameId": "" }`；空则整表恢复 |

---

## 6. 管理 UI

`/admin` 增加页签 **「难度参数」**：

1. 选择游戏（8 款）
2. 表格编辑六档字段；24 点另编辑 `cuts`
3. **保存** → PUT
4. **恢复本游戏默认** → reset（二次确认）
5. 前端基础校验 + 后端再校验

风格与现有管理页一致。

---

## 7. 游戏接入

- 共享加载：`FGB.loadDifficulty(gameId)`（或等价），在开局/`applyDiff` 前合并进本地 `DIFF`/`TIERS`。
- 拉取失败：回退代码内置默认，不阻断开玩。
- 大厅与每日模式共用；每日 URL 仍传 `tier`（+seed 等）。
- 24 点：`poolForTier` / 抽题路径接入 cuts 重划 + min/max 过滤。

覆盖：`24points`、`schulte`、`stroop`、`cancel`、`simon`、`spot-diff`、`maze`、`sudoku`。

---

## 8. 测试要点

- 默认 GET 与当前硬编码一致（抽样断言）
- PUT 非法参数 400；合法后 GET 反映变更
- reset 单游戏 / 整表
- 游戏页加载后使用覆盖参数（可用 API 测 + 关键 JS 路径手测）
- 24 点：改 min/max 后池子不含越界题；cuts 变更改变档归属
- 管理员未登录写接口 401

---

## 9. 实现顺序建议

1. `app/difficulty.py` 默认表 + 读写/校验 + API  
2. 管理页「难度参数」  
3. `fgb-client` / 小模块 `loadDifficulty`  
4. 逐游戏合并 DIFF；最后 24 点 cuts + 过滤  
5. 测试与文档
