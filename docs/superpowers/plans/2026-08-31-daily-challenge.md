# 每日挑战 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现大厅「每日挑战」串联闯关：管理员模板驱动、当日 seed 锁定题面、分关/总计时、退出记成绩、独立挑战榜、首次设密的管理入口。

**Architecture:** FastAPI 三份 JSON（admin / challenges / runs）；`GET /daily/today` 懒生成当日组合；闯关壳 iframe 加载各游戏 `?daily=1&tier=&seed=`；游戏用 mulberry32(seed) 出题并通过 `postMessage` 回报关卡完成。游戏源在 `games/*/generate*.py`（及 schulte `build_page.py`），改完须重新 generate 同步到 `web/games/`。

**Tech Stack:** Python 3.10+、FastAPI、pytest、静态 HTML/CSS/JS；本地 `data/*.json` 存储（沿用 `app/storage.py`）。

## Global Constraints

- 规格：`docs/superpowers/specs/2026-08-31-daily-challenge-design.md`
- 日历日：服务端**本机本地** `YYYY-MM-DD`
- 可玩游戏（模板默认全选）：`24points` `schulte` `stroop` `cancel` `simon` `spot-diff` `maze` `sudoku`（不含解法库）
- 难度档：`intro` `simple` `normal` `hard` `master` `god`
- 历史组合最多 20 条；重生成**不清空**当日 runs
- 管理员鉴权头：`X-Admin-Token`；密码 `sha256(salt + password)`；session ~12h
- 每日模式**不**调用 `/api/v1/scores`
- 测试须 `monkeypatch` `app.storage.DATA_DIR` 到临时目录，避免污染真实 `data/`
- C++ 规范不适用；前端保持现有无构建、原生 JS 风格

## File map

| 文件 | 职责 |
|------|------|
| `app/daily_admin.py` | 密码、session、模板 CRUD |
| `app/daily_challenges.py` | 当日组合生成、跨日归档、重生成、history≤20 |
| `app/daily_runs.py` | 开跑 / 进度 PATCH / 挑战榜排序 |
| `app/main.py` | 挂 API + `/daily` `/admin` 等页面路由 |
| `web/js/fgb-daily.js` | 解析 daily 查询参数、seeded RNG、postMessage 完成 |
| `web/js/fgb-client.js` | 可选：封装 daily/admin API（或页面内直接 fetch） |
| `web/admin.html` | 设密/登录/模板/重生成/历史 |
| `web/daily.html` | 闯关壳 |
| `web/daily-leaderboard.html` | 挑战榜 |
| `web/index.html` | 每日挑战卡 + 管理入口 |
| `games/*/generate*.py` 等 | 注入 daily 模式适配 |
| `tests/test_daily_*.py` | 后端与页面冒烟 |

---

### Task 1: Admin 密码 / session / 模板

**Files:**
- Create: `app/daily_admin.py`
- Create: `tests/test_daily_admin.py`
- Modify: none yet（Task 4 再挂路由）

**Interfaces:**
- Produces:
  - `default_template() -> dict` → `{"stages": [{"gameId": str, "tier": str}, ...]}`
  - `admin_status(token: Optional[str]) -> dict` → `{hasPassword, authenticated}`
  - `setup_password(password: str) -> dict` → `{token, expiresAt}`；已设密则 `ValueError`
  - `login(password: str) -> dict` → `{token, expiresAt}`；错密 `ValueError`
  - `logout(token: str) -> None`
  - `require_admin(token: Optional[str]) -> None`；无效则 raise `PermissionError`
  - `get_template() -> dict`
  - `put_template(stages: list) -> dict`；空/非法 gameId/tier → `ValueError`
- Consumes: `app.storage.load_json/save_json`；`app.rank_config.STANDARD_TIER_IDS`、`RANKABLE_GAMES`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_daily_admin.py
import pytest
from pathlib import Path

from app import daily_admin as da


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_setup_login_and_status():
    st = da.admin_status(None)
    assert st == {"hasPassword": False, "authenticated": False}
    out = da.setup_password("secret123")
    assert out["token"]
    assert da.admin_status(out["token"])["authenticated"] is True
    with pytest.raises(ValueError):
        da.setup_password("again")
    tok2 = da.login("secret123")["token"]
    assert da.admin_status(tok2)["authenticated"] is True
    with pytest.raises(ValueError):
        da.login("wrong")


def test_template_default_and_put():
    t = da.get_template()
    assert len(t["stages"]) == 8
    assert t["stages"][0]["tier"] == "normal"
    da.put_template([{"gameId": "schulte", "tier": "hard"}, {"gameId": "sudoku", "tier": "simple"}])
    assert da.get_template()["stages"][0]["gameId"] == "schulte"
    with pytest.raises(ValueError):
        da.put_template([])
    with pytest.raises(ValueError):
        da.put_template([{"gameId": "nope", "tier": "normal"}])
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd family_game_box
python -m pytest tests/test_daily_admin.py -v
```

Expected: `ModuleNotFoundError` or import error for `app.daily_admin`

- [ ] **Step 3: Implement `app/daily_admin.py`**

```python
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.rank_config import RANKABLE_GAMES, STANDARD_TIER_IDS, tier_label
from app.storage import load_json, save_json

STORE = "daily_admin.json"
SESSION_HOURS = 12
PLAYABLE_IDS = [g["id"] for g in RANKABLE_GAMES]


def _empty() -> Dict[str, Any]:
    return {
        "version": 1,
        "passwordHash": "",
        "salt": "",
        "sessionToken": "",
        "sessionExpiresAt": "",
        "template": default_template(),
    }


def default_template() -> Dict[str, Any]:
    return {"stages": [{"gameId": gid, "tier": "normal"} for gid in PLAYABLE_IDS]}


def _load() -> Dict[str, Any]:
    data = load_json(STORE, _empty())
    if not isinstance(data.get("template"), dict):
        data["template"] = default_template()
    return data


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def _hash(salt: str, password: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _issue_session(data: Dict[str, Any]) -> Dict[str, str]:
    token = secrets.token_urlsafe(24)
    exp = _now() + timedelta(hours=SESSION_HOURS)
    data["sessionToken"] = token
    data["sessionExpiresAt"] = exp.isoformat()
    _save(data)
    return {"token": token, "expiresAt": data["sessionExpiresAt"]}


def _session_ok(data: Dict[str, Any], token: Optional[str]) -> bool:
    if not token or not data.get("sessionToken") or token != data["sessionToken"]:
        return False
    raw = data.get("sessionExpiresAt") or ""
    try:
        exp = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return _now() <= exp


def admin_status(token: Optional[str] = None) -> Dict[str, Any]:
    data = _load()
    return {
        "hasPassword": bool(data.get("passwordHash")),
        "authenticated": _session_ok(data, token),
    }


def setup_password(password: str) -> Dict[str, str]:
    password = (password or "").strip()
    if len(password) < 4:
        raise ValueError("password too short")
    data = _load()
    if data.get("passwordHash"):
        raise ValueError("password already set")
    salt = secrets.token_hex(16)
    data["salt"] = salt
    data["passwordHash"] = _hash(salt, password)
    return _issue_session(data)


def login(password: str) -> Dict[str, str]:
    data = _load()
    if not data.get("passwordHash"):
        raise ValueError("password not set")
    if _hash(data.get("salt") or "", password or "") != data["passwordHash"]:
        raise ValueError("invalid password")
    return _issue_session(data)


def logout(token: str) -> None:
    data = _load()
    if token and token == data.get("sessionToken"):
        data["sessionToken"] = ""
        data["sessionExpiresAt"] = ""
        _save(data)


def require_admin(token: Optional[str]) -> None:
    if not _session_ok(_load(), token):
        raise PermissionError("admin auth required")


def get_template() -> Dict[str, Any]:
    data = _load()
    stages = data.get("template", {}).get("stages") or []
    if not stages:
        return default_template()
    return {"stages": list(stages)}


def put_template(stages: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not stages:
        raise ValueError("template stages empty")
    clean: List[Dict[str, str]] = []
    for s in stages:
        gid = str(s.get("gameId") or "").strip()
        tier = str(s.get("tier") or "").strip()
        if gid not in PLAYABLE_IDS:
            raise ValueError("unknown gameId: %s" % gid)
        if tier not in STANDARD_TIER_IDS:
            raise ValueError("invalid tier: %s" % tier)
        clean.append({"gameId": gid, "tier": tier})
    data = _load()
    data["template"] = {"stages": clean}
    _save(data)
    return get_template()
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_daily_admin.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/daily_admin.py tests/test_daily_admin.py
git commit -m "feat(daily): add admin password, session, and template store"
```

---

### Task 2: 当日组合生成 / 归档 / 重生成

**Files:**
- Create: `app/daily_challenges.py`
- Create: `tests/test_daily_challenges.py`

**Interfaces:**
- Consumes: `daily_admin.get_template`；`rank_config.tier_label`、`RANKABLE_GAMES`
- Produces:
  - `local_today() -> str`
  - `ensure_today(source: str = "auto") -> dict`  # 返回 current combo；跨日归档后按模板生成
  - `regenerate() -> dict`  # 归档 current（若有）后按模板生成 `source=admin`
  - `get_history() -> list`  # 最多 20
  - combo shape: `{comboId, date, createdAt, source, stages:[{gameId,title,tier,tierLabel,seed}]}`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_daily_challenges.py
import pytest
from app import daily_admin as da
from app import daily_challenges as dc


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def test_ensure_today_stable_same_day():
    a = dc.ensure_today()
    b = dc.ensure_today()
    assert a["comboId"] == b["comboId"]
    assert a["date"] == dc.local_today()
    assert len(a["stages"]) == 8
    assert all("seed" in s for s in a["stages"])


def test_regenerate_archives_and_keeps_history_cap(monkeypatch):
    first = dc.ensure_today()
    second = dc.regenerate()
    assert first["comboId"] != second["comboId"]
    hist = dc.get_history()
    assert len(hist) == 1
    assert hist[0]["comboId"] == first["comboId"]
    # force many regenerations
    for _ in range(25):
        dc.regenerate()
    assert len(dc.get_history()) == 20


def test_cross_day_rolls(monkeypatch):
    c1 = dc.ensure_today()
    monkeypatch.setattr(dc, "local_today", lambda: "2099-01-02")
    c2 = dc.ensure_today()
    assert c2["date"] == "2099-01-02"
    assert c1["comboId"] in [h["comboId"] for h in dc.get_history()]
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_daily_challenges.py -v
```

- [ ] **Step 3: Implement `app/daily_challenges.py`**

```python
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.daily_admin import get_template
from app.rank_config import RANKABLE_GAMES, tier_label
from app.storage import load_json, save_json

STORE = "daily_challenges.json"
HISTORY_MAX = 20
_TITLES = {g["id"]: g["title"] for g in RANKABLE_GAMES}


def _empty() -> Dict[str, Any]:
    return {"version": 1, "current": None, "history": []}


def _load() -> Dict[str, Any]:
    return load_json(STORE, _empty())


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def local_today() -> str:
    return datetime.now().astimezone().date().isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_combo(source: str) -> Dict[str, Any]:
    tmpl = get_template()
    stages_in = tmpl.get("stages") or []
    if not stages_in:
        raise ValueError("empty template")
    stages = []
    for s in stages_in:
        gid = s["gameId"]
        tier = s["tier"]
        stages.append(
            {
                "gameId": gid,
                "title": _TITLES.get(gid, gid),
                "tier": tier,
                "tierLabel": tier_label(tier),
                "seed": secrets.randbelow(2**31 - 1) + 1,
            }
        )
    return {
        "comboId": str(uuid.uuid4()),
        "date": local_today(),
        "createdAt": _now_iso(),
        "source": source,
        "stages": stages,
    }


def _push_history(data: Dict[str, Any], combo: Dict[str, Any]) -> None:
    hist: List[Dict[str, Any]] = list(data.get("history") or [])
    hist.insert(0, combo)
    data["history"] = hist[:HISTORY_MAX]


def ensure_today(source: str = "auto") -> Dict[str, Any]:
    data = _load()
    cur = data.get("current")
    today = local_today()
    if isinstance(cur, dict) and cur.get("date") == today:
        return cur
    if isinstance(cur, dict) and cur.get("comboId"):
        _push_history(data, cur)
    combo = _build_combo(source)
    data["current"] = combo
    _save(data)
    return combo


def regenerate() -> Dict[str, Any]:
    data = _load()
    cur = data.get("current")
    if isinstance(cur, dict) and cur.get("comboId"):
        _push_history(data, cur)
    combo = _build_combo("admin")
    data["current"] = combo
    _save(data)
    return combo


def get_history() -> List[Dict[str, Any]]:
    data = _load()
    return list(data.get("history") or [])[:HISTORY_MAX]


def get_current() -> Any:
    return _load().get("current")
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_daily_challenges.py tests/test_daily_admin.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/daily_challenges.py tests/test_daily_challenges.py
git commit -m "feat(daily): generate and archive daily challenge combos"
```

---

### Task 3: Runs + 挑战榜

**Files:**
- Create: `app/daily_runs.py`
- Create: `tests/test_daily_runs.py`

**Interfaces:**
- Consumes: `daily_challenges.ensure_today`；`terminals.get_terminal`
- Produces:
  - `start_run(terminal_id: str) -> dict`
  - `patch_run(terminal_id, run_id, body: dict) -> dict`  
    body 字段：`action` ∈ `stage_done|exit|finish`；`stageIndex`；`timeMs`；`totalTimeMs`；`stageResults` 可选增量
  - `leaderboard(date: Optional[str] = None, limit: int = 50) -> dict` → `{date, items:[...]}`
  - 排序：`finished` 优先 → `stagesDone` 降序 → `totalTimeMs` 升序

- [ ] **Step 1: Write failing tests**

```python
# tests/test_daily_runs.py
import uuid
import pytest
from app import daily_challenges as dc
from app import daily_runs as dr
from app.terminals import register_terminal


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    yield


def _tid():
    return str(uuid.uuid4())


def test_start_exit_and_finish_leaderboard():
    t1, t2 = _tid(), _tid()
    register_terminal(t1, "甲")
    register_terminal(t2, "乙")
    dc.ensure_today()
    r1 = dr.start_run(t1)
    assert r1["status"] == "running"
    dr.patch_run(t1, r1["runId"], {
        "action": "stage_done", "stageIndex": 0, "timeMs": 1000, "totalTimeMs": 1200,
        "stage": {"gameId": "24points", "tier": "normal", "timeMs": 1000, "completed": True},
    })
    exited = dr.patch_run(t1, r1["runId"], {
        "action": "exit", "totalTimeMs": 5000,
        "stage": {"gameId": "schulte", "tier": "normal", "timeMs": 500, "completed": False},
    })
    assert exited["status"] == "exited"
    assert exited["stagesDone"] == 1

    r2 = dr.start_run(t2)
    n = len(r2["stages"])
    for i in range(n):
        st = r2["stages"][i]
        action = "finish" if i == n - 1 else "stage_done"
        dr.patch_run(t2, r2["runId"], {
            "action": action, "stageIndex": i, "timeMs": 800, "totalTimeMs": (i + 1) * 1000,
            "stage": {"gameId": st["gameId"], "tier": st["tier"], "timeMs": 800, "completed": True},
        })
    board = dr.leaderboard()
    assert board["items"][0]["nickname"] == "乙"
    assert board["items"][0]["status"] == "finished"
    assert board["items"][1]["status"] == "exited"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
python -m pytest tests/test_daily_runs.py -v
```

- [ ] **Step 3: Implement `app/daily_runs.py`**

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.daily_challenges import ensure_today, local_today
from app.storage import load_json, save_json
from app.terminals import get_terminal

STORE = "daily_runs.json"


def _empty() -> Dict[str, Any]:
    return {"version": 1, "runs": {}}


def _load() -> Dict[str, Any]:
    return load_json(STORE, _empty())


def _save(data: Dict[str, Any]) -> None:
    save_json(STORE, data)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run(terminal_id: str) -> Dict[str, Any]:
    term = get_terminal(terminal_id)
    if not term:
        raise ValueError("terminal not registered")
    combo = ensure_today()
    run_id = str(uuid.uuid4())
    run = {
        "runId": run_id,
        "comboId": combo["comboId"],
        "date": combo["date"],
        "terminalId": terminal_id,
        "nickname": term.get("nickname") or "",
        "status": "running",
        "startedAt": _now(),
        "endedAt": "",
        "totalTimeMs": 0,
        "stagesDone": 0,
        "stageResults": [],
        "stages": combo["stages"],
    }
    data = _load()
    data.setdefault("runs", {})[run_id] = run
    _save(data)
    return run


def _append_stage(run: Dict[str, Any], stage: Optional[Dict[str, Any]]) -> None:
    if not isinstance(stage, dict):
        return
    entry = {
        "gameId": str(stage.get("gameId") or ""),
        "tier": str(stage.get("tier") or ""),
        "timeMs": int(stage.get("timeMs") or 0),
        "completed": bool(stage.get("completed")),
    }
    run.setdefault("stageResults", []).append(entry)
    if entry["completed"]:
        run["stagesDone"] = int(run.get("stagesDone") or 0) + 1


def patch_run(terminal_id: str, run_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    run = (data.get("runs") or {}).get(run_id)
    if not isinstance(run, dict):
        raise ValueError("run not found")
    if run.get("terminalId") != terminal_id:
        raise PermissionError("not your run")
    if run.get("status") != "running":
        raise ValueError("run not running")
    action = str(body.get("action") or "")
    stage = body.get("stage")
    if "totalTimeMs" in body:
        run["totalTimeMs"] = int(body.get("totalTimeMs") or 0)
    if action == "stage_done":
        st = dict(stage or {})
        st["completed"] = True
        _append_stage(run, st)
    elif action == "exit":
        if isinstance(stage, dict):
            st = dict(stage)
            st["completed"] = bool(st.get("completed"))
            _append_stage(run, st)
        run["status"] = "exited"
        run["endedAt"] = _now()
    elif action == "finish":
        if isinstance(stage, dict):
            st = dict(stage)
            st["completed"] = True
            _append_stage(run, st)
        run["status"] = "finished"
        run["endedAt"] = _now()
    else:
        raise ValueError("invalid action")
    data["runs"][run_id] = run
    _save(data)
    return run


def leaderboard(date: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    day = date or local_today()
    items: List[Dict[str, Any]] = []
    for run in (_load().get("runs") or {}).values():
        if not isinstance(run, dict):
            continue
        if run.get("date") != day:
            continue
        if run.get("status") == "running":
            continue
        items.append(
            {
                "runId": run.get("runId"),
                "comboId": run.get("comboId"),
                "nickname": run.get("nickname"),
                "status": run.get("status"),
                "stagesDone": int(run.get("stagesDone") or 0),
                "totalTimeMs": int(run.get("totalTimeMs") or 0),
                "stageResults": run.get("stageResults") or [],
                "endedAt": run.get("endedAt") or "",
            }
        )

    def _key(it: Dict[str, Any]):
        finished = 0 if it["status"] == "finished" else 1
        return (finished, -it["stagesDone"], it["totalTimeMs"])

    items.sort(key=_key)
    return {"date": day, "items": items[: max(1, min(limit, 100))]}
```

- [ ] **Step 4: Run — expect PASS**

```bash
python -m pytest tests/test_daily_runs.py tests/test_daily_challenges.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/daily_runs.py tests/test_daily_runs.py
git commit -m "feat(daily): add challenge runs and leaderboard ranking"
```

---

### Task 4: 挂载 HTTP API 与页面路由

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_daily_api.py`
- Create placeholders if missing: `web/daily.html`, `web/daily-leaderboard.html`, `web/admin.html`（可先放最小 HTML，Task 5–6 填满）

**Interfaces:**
- 公开：`GET /api/v1/daily/today`、`POST /api/v1/daily/runs`、`PATCH /api/v1/daily/runs/{runId}`、`GET /api/v1/daily/leaderboard`
- 管理：`/api/v1/admin/status|setup|login|logout`、`GET/PUT /api/v1/admin/daily/template`、`POST .../regenerate`、`GET .../history`
- 页面：`GET /daily`、`GET /daily/leaderboard`、`GET /admin`
- 错误：`ValueError→400`，`PermissionError→401`

- [ ] **Step 1: Write API tests**（tmp DATA_DIR fixture + register terminal）

覆盖：today 自动生成；未注册不能 start run；setup→login→put template→regenerate；无 token regenerate→401；leaderboard 200；`/daily` `/admin` 返回 200。

- [ ] **Step 2: Run — expect FAIL**（404）

- [ ] **Step 3: Wire `main.py`**

在现有 imports 下增加 daily/admin 模块与 Pydantic body；映射 header `X-Admin-Token`；页面 `FileResponse` 与 leaderboard 页同模式。创建三个最小 HTML：

```html
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>占位</title></head>
<body><p>占位</p></body></html>
```

- [ ] **Step 4: pytest PASS**

```bash
python -m pytest tests/test_daily_api.py tests/test_daily_admin.py tests/test_daily_challenges.py tests/test_daily_runs.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_daily_api.py web/daily.html web/daily-leaderboard.html web/admin.html
git commit -m "feat(daily): expose daily challenge and admin HTTP APIs"
```

---

### Task 5: `fgb-daily.js` + 管理页

**Files:**
- Create: `web/js/fgb-daily.js`
- Modify: `web/admin.html`（完整 UI）
- Modify: `tests/test_daily_api.py`（断言 admin 页含关键文案）

**Interfaces (`fgb-daily.js` 挂 `window.FGBDaily`):**
- `parseQuery() -> {daily, runId, tier, seed, stageIndex}`
- `isDaily() -> bool`
- `makeRng(seed: number) -> () => number`  # mulberry32，返回 [0,1)
- `installMathRandom(seed)` / 可选：返回 restore 函数
- `notifyStageDone(timeMs: number)` → `parent.postMessage({type:"fgb-daily-stage-done", timeMs}, "*")`
- `notifyAbort()` → `{type:"fgb-daily-abort"}`

- [ ] **Step 1: 实现 `web/js/fgb-daily.js`**（完整 mulberry32）

```javascript
(function (global) {
  "use strict";
  function parseQuery() {
    var q = new URLSearchParams(global.location.search || "");
    return {
      daily: q.get("daily") === "1",
      runId: q.get("runId") || "",
      tier: q.get("tier") || "normal",
      seed: Number(q.get("seed") || "0") || 0,
      stageIndex: Number(q.get("stageIndex") || "0") || 0,
    };
  }
  function makeRng(seed) {
    var t = (seed >>> 0) || 1;
    return function () {
      t += 0x6D2B79F5;
      var r = Math.imul(t ^ (t >>> 15), 1 | t);
      r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  }
  function installMathRandom(seed) {
    var rng = makeRng(seed);
    var original = Math.random;
    Math.random = rng;
    return function restore() { Math.random = original; };
  }
  function notifyStageDone(timeMs) {
    if (global.parent && global.parent !== global) {
      global.parent.postMessage({ type: "fgb-daily-stage-done", timeMs: timeMs | 0 }, "*");
    }
  }
  function notifyAbort() {
    if (global.parent && global.parent !== global) {
      global.parent.postMessage({ type: "fgb-daily-abort" }, "*");
    }
  }
  global.FGBDaily = {
    parseQuery: parseQuery,
    isDaily: function () { return parseQuery().daily; },
    makeRng: makeRng,
    installMathRandom: installMathRandom,
    notifyStageDone: notifyStageDone,
    notifyAbort: notifyAbort,
  };
})(window);
```

- [ ] **Step 2: 实现 `web/admin.html`**

风格对齐大厅（`--ink/--accent/--paper`）。区块：
1. status 加载 → 无密码显示设密表单；有密码未登录显示登录；已登录显示主面板
2. 主面板：模板列表（每行：游戏名、难度 select、上移/下移/删除）；「添加游戏」；保存模板
3. 今日组合只读 +「重新生成」确认
4. 历史列表
5. 登出 / 回大厅

API：`X-Admin-Token` from `sessionStorage.fgb_admin_token`。

- [ ] **Step 3: 手动冒烟**（起服务）

```bash
# 在 family_game_box 根目录
python -m uvicorn app.main:app --host 127.0.0.1 --port 18029
```

浏览器打开 `http://127.0.0.1:18029/admin`：设密 → 改模板保存 → 重生成。

- [ ] **Step 4: Commit**

```bash
git add web/js/fgb-daily.js web/admin.html tests/test_daily_api.py
git commit -m "feat(daily): add admin UI and shared daily JS helper"
```

---

### Task 6: 闯关壳 + 挑战榜 + 大厅入口

**Files:**
- Modify: `web/daily.html`（完整）
- Modify: `web/daily-leaderboard.html`
- Modify: `web/index.html`
- Modify: `tests/test_api.py`（大厅含「每日挑战」、`/admin` 链）

**闯关壳行为（必须）：**
1. `GET /api/v1/daily/today` 展示关卡列表
2. 「开始挑战」：确保已注册 → `POST /api/v1/daily/runs` → 显示 iframe 区 + 顶栏计时
3. iframe `src` = 游戏 path + query（从 `GET /api/v1/games` 或写死 path map）：
   - `24points` → `/games/24points/play.html`
   - 其余 → `/games/{id}/`（`spot-diff` 保持连字符）
4. `message` 监听 `fgb-daily-stage-done` → PATCH `stage_done` → 下一关；最后一关用 `finish`
5. `fgb-daily-abort` 或顶栏退出 → 确认 → PATCH `exit`
6. 结算页；链到 `/daily/leaderboard`
7. 总计时 `setInterval` 自 startedAt；本关用时自 stageEnteredAt

**大厅：**
- 网格**最前**加每日挑战卡 → `/daily`
- topbar 加「挑战榜」→ `/daily/leaderboard`
- 页脚小字「管理」→ `/admin`
- 锁定逻辑：每日挑战卡与可玩卡一样未注册锁定

- [ ] **Step 1: 实现三页 + 改大厅**

- [ ] **Step 2: 更新 `tests/test_api.py`**

```python
def test_lobby_html():
    ...
    assert "每日挑战" in text
    assert 'href="/daily"' in text
    assert 'href="/admin"' in text
```

- [ ] **Step 3: pytest 相关用例 PASS**

```bash
python -m pytest tests/test_api.py tests/test_daily_api.py -v
```

- [ ] **Step 4: Commit**

```bash
git add web/daily.html web/daily-leaderboard.html web/index.html tests/test_api.py
git commit -m "feat(daily): add run shell, challenge board, and lobby entry"
```

---

### Task 7: 游戏适配 — 共享约定 + 舒尔特样板

**Files:**
- Modify: `games/schulte/index.html`（或 `build_page.py` 生成用源）
- Run: `python games/schulte/build_page.py` 同步 `web/games/schulte/`
- 各页 `<script src="/js/fgb-daily.js"></script>`（在游戏脚本前）

**适配清单（舒尔特完整做完作为样板）：**
1. 若 `FGBDaily.isDaily()`：读 `tier`/`seed`，`installMathRandom(seed)`，跳过模式选择，直接开**单局**休闲等价流程（打完一局即完成）
2. 单局完成时：若 daily，调用 `FGBDaily.notifyStageDone(elapsedMs)`，**不要** `fgbSubmitScore`
3. 隐藏「返回大厅」或改为 `notifyAbort`（iframe 内回大厅会破坏壳）
4. 用同一 seed 两次进入，格子排列应一致（可手测）

- [ ] **Step 1: 改 schulte 源并 build**

```bash
python games/schulte/build_page.py
```

- [ ] **Step 2: 手测** iframe URL  
`http://127.0.0.1:18029/games/schulte/?daily=1&tier=normal&seed=12345&stageIndex=0`  
完成应 postMessage（可在父页 console 听）。

- [ ] **Step 3: Commit**

```bash
git add games/schulte web/games/schulte
git commit -m "feat(daily): adapt schulte for seeded daily stage mode"
```

---

### Task 8: 其余 7 款游戏适配

**Files（改 generate 源后重新生成）：**
- `games/24points/generate_play.py` → `python games/24points/generate_play.py`
- `games/stroop/generate.py`
- `games/cancel/generate.py`
- `games/simon/generate.py`
- `games/spot_diff/generate.py`
- `games/maze/generate.py`
- `games/sudoku/generate.py`

每款执行与 Task 7 **相同清单**：daily 检测、seed RNG、跳过选难、单局完成 `notifyStageDone`、禁普通 scores、禁破坏性回大厅。

注意：
- 各游戏现有 `Math.random` / `randInt`：daily 下在开局前 `installMathRandom`
- 挑战模式多题（如 10 题）**不要**启用；每日只打 1 局
- `spot_diff` 目录名下划线，web 路径是 `spot-diff`

- [ ] **Step 1: 逐个改 generate + 跑脚本同步 web**

- [ ] **Step 2: 冒烟** `/daily` 开挑战，至少打完 2–3 关能自动切关；退出上榜

- [ ] **Step 3: 全量 pytest**

```bash
python -m pytest -v
```

- [ ] **Step 4: Commit**

```bash
git add games web/games
git commit -m "feat(daily): adapt remaining games for daily seeded stages"
```

---

### Task 9: 收尾核对

- [ ] **Step 1: Spec 对照清单**（逐项打勾）

| Spec 项 | 验证 |
|---------|------|
| 串联闯关 | `/daily` 顺序切关 |
| 分关+总计时 | 顶栏两计时 |
| 退出记成绩 / 再开新 run | PATCH exit；再开始新 runId |
| 独立榜排序 | finished > stagesDone > time |
| 首次访问自动生成 | GET today |
| 管理员重生成、history≤20 | admin UI + 单测 |
| 当日成绩不清空 | regenerate 后 leaderboard 仍有旧 run |
| seed 锁题 | 同 seed 两次题面一致 |
| 首次设密管理入口 | `/admin` |

- [ ] **Step 2: 若 build 发布需要** — 将新 html/js 纳入 `scripts/build.bat` 的 copy（`web/daily*.html` `web/admin.html` 已随 `copy index/leaderboard` 模式显式 copy，或确认 xcopy `web/js` 覆盖 `fgb-daily.js`）

在 `build.bat` 中 `copy leaderboard` 旁增加：

```bat
copy /Y "web\daily.html" "dist\web\daily.html" >nul
copy /Y "web\daily-leaderboard.html" "dist\web\daily-leaderboard.html" >nul
copy /Y "web\admin.html" "dist\web\admin.html" >nul
```

- [ ] **Step 3: Commit（如有 build 变更）**

```bash
git add scripts/build.bat
git commit -m "build: include daily challenge and admin pages in dist"
```

---

## Plan self-review

1. **Spec coverage:** 数据模型、API、闯关壳、管理页、8 游戏 seed 适配、榜、history20、成绩不清空 — 均有对应 Task。
2. **Placeholders:** 无 TBD；Task 3 实现用文字要点 + 测试锁定行为（实现代码在执行时按接口写全）。
3. **Types:** `comboId`/`runId`/`stagesDone`/`totalTimeMs`/`fgb-daily-stage-done` 命名前后一致。
