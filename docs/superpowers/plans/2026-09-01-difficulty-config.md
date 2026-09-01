# 全局难度参数配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理端可编辑各游戏六档难度参数；大厅与每日挑战共用；含 24 点 cuts + min/max 硬过滤；支持按游戏恢复默认。

**Architecture:** `app/difficulty.py` 持有出厂默认表与 `data/difficulty.json` 覆盖合并；公开 GET + 管理员 PUT/reset；前端 `FGB.loadDifficulty(gameId)` 开局合并本地 DIFF；24 点运行时按 cuts 重划档并过滤数字范围。

**Tech Stack:** Python 3.10+、FastAPI、pytest、静态 HTML/JS；`app/storage.py` JSON 存储。

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-01-difficulty-config-design.md`
- 六档 id：`intro` `simple` `normal` `hard` `master` `god`
- 游戏 id：`24points` `schulte` `stroop` `cancel` `simon` `spot-diff` `maze` `sudoku`
- 保存后新开局立即生效；进行中对局不改
- 管理员鉴权：`X-Admin-Token`（与 daily admin 相同）
- 测试须 monkeypatch `app.storage.DATA_DIR` 到临时目录
- 24 点：cuts 重划 + `minNum`/`maxNum` 硬过滤；空池按 spec 回退

## File map

| 文件 | 职责 |
|------|------|
| `app/difficulty.py` | 默认表、合并、校验、读写、reset |
| `app/main.py` | 挂载 difficulty API |
| `web/admin.html` | 「难度参数」页签 |
| `web/js/fgb-client.js` | `loadDifficulty` |
| `games/*/generate*.py` + schulte | 开局合并 DIFF；24 点过滤 |
| `tests/test_difficulty.py` | 后端单测 |
| `tests/test_difficulty_api.py` | HTTP 测 |

---

### Task 1: difficulty 模块（默认表 + 校验 + 读写）

**Files:**
- Create: `app/difficulty.py`
- Create: `tests/test_difficulty.py`

**Interfaces:**
- Produces:
  - `default_difficulty() -> dict`
  - `get_difficulty(game_id: Optional[str] = None) -> dict`
  - `put_difficulty(games_partial: dict) -> dict`  # 合并写入，校验
  - `reset_difficulty(game_id: Optional[str] = None) -> dict`
- Consumes: `app.storage.load_json/save_json`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_difficulty.py
import pytest
from app import difficulty as diff


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_get_defaults_has_eight_games():
    data = diff.get_difficulty()
    for gid in ("24points", "schulte", "stroop", "cancel", "simon", "spot-diff", "maze", "sudoku"):
        assert gid in data["games"]
        assert "normal" in data["games"][gid]["tiers"]


def test_put_schulte_and_get():
    diff.put_difficulty({
        "schulte": {"tiers": {"normal": {"size": 6, "reverse": True, "label": "普通*"}}}
    })
    g = diff.get_difficulty("schulte")
    assert g["games"]["schulte"]["tiers"]["normal"]["size"] == 6
    assert g["games"]["schulte"]["tiers"]["intro"]["size"] == 3  # untouched default


def test_put_invalid_sudoku_rejects():
    with pytest.raises(ValueError):
        diff.put_difficulty({"sudoku": {"tiers": {"intro": {"size": 5, "givens": 3, "label": "x"}}}})


def test_reset_one_game():
    diff.put_difficulty({"maze": {"tiers": {"intro": {"size": 7, "label": "入门"}}}})
    diff.reset_difficulty("maze")
    assert diff.get_difficulty("maze")["games"]["maze"]["tiers"]["intro"]["size"] == 9


def test_24points_cuts_and_range():
    diff.put_difficulty({
        "24points": {
            "cuts": [0.1, 0.2, 0.4, 0.6, 0.8, 1.01],
            "tiers": {"intro": {"minNum": 1, "maxNum": 9, "label": "入门", "desc": ""}},
        }
    })
    t = diff.get_difficulty("24points")["games"]["24points"]
    assert t["cuts"][0] == 0.1
    assert t["tiers"]["intro"]["maxNum"] == 9
```

- [ ] **Step 2: Run — expect FAIL** (`pytest tests/test_difficulty.py -v`)

- [ ] **Step 3: Implement `app/difficulty.py`**

内置 `DEFAULTS`：从现网各游戏 DIFF 抄齐（schulte/sudoku/stroop/cancel/simon/spot-diff/maze；24points 默认 cuts=`[0.12,0.28,0.50,0.72,0.88,1.01]`，每档合理 min/max/label/desc）。

实现要点：
- `_deep_merge(defaults, stored)`
- `put_difficulty`：对每个提交的 game 跑 `validate_game(game_id, payload)`，再写入 stored 的该游戏整块（或 deep merge tiers）
- `reset_difficulty`：删 stored 中该 key 或清空 games

校验函数按 spec §4.1 / §4.2 实现。

- [ ] **Step 4: pytest PASS**

- [ ] **Step 5: Commit** `feat(difficulty): add difficulty store with defaults and validation`

---

### Task 2: HTTP API

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_difficulty_api.py`

**Interfaces:**
- `GET /api/v1/difficulty`
- `GET /api/v1/difficulty/defaults`
- `PUT /api/v1/admin/difficulty` body `{ "games": { ... } }`
- `POST /api/v1/admin/difficulty/reset` body `{ "gameId": "" }`

- [ ] **Step 1: API tests**（tmp DATA_DIR + admin setup/login token）

覆盖：匿名 GET 200；无 token PUT 401；setup 后 PUT schulte 成功；reset 恢复。

- [ ] **Step 2: Wire main.py**（复用 daily_admin.require_admin）

- [ ] **Step 3: pytest PASS → Commit** `feat(difficulty): expose difficulty HTTP APIs`

---

### Task 3: 管理页「难度参数」

**Files:**
- Modify: `web/admin.html`

- [ ] **Step 1:** 增加页签切换：模板 | 难度参数 |（保留今日组合/历史）

- [ ] **Step 2:** 难度页：游戏 select → 渲染六档表单（按 gameId 字段 schema 写死在 JS 的 `FIELD_SCHEMA`）

```javascript
var FIELD_SCHEMA = {
  schulte: [{ key: "size", type: "number" }, { key: "reverse", type: "bool" }, { key: "label", type: "text" }],
  sudoku: [{ key: "size", type: "number" }, { key: "givens", type: "number" }, { key: "label", type: "text" }],
  // ... 其余游戏 + 24points 特殊 cuts 行
};
```

- [ ] **Step 3:** 保存 / 恢复本游戏默认（confirm）

- [ ] **Step 4:** 手测 `/admin` → Commit `feat(difficulty): add admin difficulty editor tab`

---

### Task 4: `FGB.loadDifficulty`

**Files:**
- Modify: `web/js/fgb-client.js`

**Produces:**
```javascript
FGB.loadDifficulty = function (gameId) {
  return api("/api/v1/difficulty?gameId=" + encodeURIComponent(gameId)).then(function (data) {
    return (data.games && data.games[gameId]) || null;
  }).catch(function () { return null; });
};
```

- [ ] **Step 1: 实现并导出**

- [ ] **Step 2: Commit** `feat(difficulty): add FGB.loadDifficulty client helper`

---

### Task 5: 接入 7 款注意力/逻辑游戏（不含 24 点）

**Files:** `games/schulte/index.html`、`games/{stroop,cancel,simon,spot_diff,maze,sudoku}/generate.py`  
生成后同步 `web/games/`。

**模式（每款）：**
1. 在定义 `DIFF`/`TIERS` 之后、首次 `applyDiff`/开局前：

```javascript
function mergeDifficultyConfig(cfg) {
  if (!cfg || !cfg.tiers) return;
  Object.keys(cfg.tiers).forEach(function (k) {
    if (!DIFF[k]) return;
    Object.assign(DIFF[k], cfg.tiers[k]);
  });
}
FGB.loadDifficulty("stroop").then(function (cfg) {
  mergeDifficultyConfig(cfg);
  // 若尚未开局且需要刷新文案，调用 applyDiff / updateDiffDesc
});
```

2. 每日模式：在 `startCasual`/`startChallenge` **之前**确保已 merge（可用 Promise：开局按钮或 daily boot 先 `loadDifficulty().then(start...)`）。

**舒尔特：** 合并进 `TIERS`；daily 的 `startCasual` 包在 load 之后。

- [ ] **Step 1–N:** 逐游戏改 + regenerate

- [ ] **Step 最后: Commit** `feat(difficulty): merge server difficulty into attention/logic games`

---

### Task 6: 24 点 cuts + min/max 过滤

**Files:** `games/24points/generate_play.py` → regenerate play.html

- [ ] **Step 1:** `loadDifficulty("24points")` 得到 `cuts` + tiers

- [ ] **Step 2:** 实现运行时划档：

```javascript
function assignTierByCuts(puzzles, cuts) {
  // puzzles already have hardness order: sort bank by precomputed h if available,
  // else use existing t as fallback. Prefer: keep BANK order from file (already sorted by hardness at build).
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
```

注：`bank.json` 构建时已按 hardness 排序写入；运行时用当前 cuts 重标 `t`。

- [ ] **Step 3:** `poolForTier` 后过滤：

```javascript
function inNumRange(p, minN, maxN) {
  return p.n.every(function (x) { return x >= minN && x <= maxN; });
}
```

空池按 spec 回退。

- [ ] **Step 4:** 手测改 intro maxNum=5 后入门题均 ≤5 → Commit `feat(difficulty): apply configurable cuts and number range to 24points`

---

### Task 7: 收尾

- [ ] **Step 1:** `pytest -q` 全绿

- [ ] **Step 2:** Spec 对照清单（API、reset、八游戏字段、24 点过滤、管理页）

- [ ] **Step 3:** 如需 push 由用户决定；本 Task 只保证本地提交齐全

---

## Plan self-review

1. Spec 覆盖：数据/API/管理UI/游戏合并/24点/reset — 均有 Task  
2. 无 TBD  
3. `get_difficulty` / `put_difficulty` / `loadDifficulty` 命名一致  
