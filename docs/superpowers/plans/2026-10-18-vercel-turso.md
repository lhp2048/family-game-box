# Vercel 部署与 Turso 存储 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同一套 FastAPI 在家里继续写本地 JSON，在 Vercel 上把同一批 JSON 文档写入 Turso，并让管理员用单独的家庭口令决定玩游戏要不要先解锁。

**Architecture:** `load_json` / `save_json` 按环境选择文件或 Turso。Turso 用 HTTP `/v2/pipeline`，每个现有 JSON 文件一行。家庭口令存在 `daily_admin.json`，用 cookie `fgb_play` 放行；开关默认关闭。Vercel 通过根目录 `index.py` 导出现有 `app`。

**Tech Stack:** FastAPI、pytest、httpx、Turso HTTP pipeline、Vercel Python Functions。

## Global Constraints

- 家里未设置 `TURSO_DATABASE_URL` 时，数据仍写 `data/*.json`，zip 安装和默认 `ROOT_PATH=/game-box`、端口 18029 不变。
- 设置了 `TURSO_DATABASE_URL` 时，文档表为 `documents(name TEXT PRIMARY KEY, body TEXT NOT NULL)`，写入是整行替换；Turso 失败抛错，接口返回 503，正文 `暂时存不上`，不得用空文档顶上。
- 家里 JSON 损坏时仍返回调用方给的默认值。
- Vercel（环境变量 `VERCEL` 有值）但没有 Turso 地址时，健康检查未就绪，不得把数据写进临时磁盘。
- Preview 使用另一份 Turso 库，不写生产库。
- 口令只存盐和 SHA-256，最短 4 个字符；cookie 值是 `代数.过期时间.HMAC-SHA256`，不含口令；`Max-Age` 30 天；`SameSite=Lax`；仅 HTTPS 加 `Secure`。
- 默认 `playGateEnabled` 为 false。更换口令，或从关闭变为打开时，`playGeneration` 加 1。只关闭不加。
- 未解锁访问受保护页面时重定向到 `/play-gate?next=`。`next` 必须以 `/` 开头且不能以 `//` 开头，否则回大厅。
- 配了 Turso 地址时拒绝上传游戏包，说明为 `请到家里的管理页上传游戏包`。
- 题库、页面、脚本不进数据库。不为家庭成员建单独账号。

规格：`docs/superpowers/specs/2026-10-18-vercel-turso-design.md`

这三块要按顺序做：存储是口令和 Vercel 的前提，拆开不能单独验收。

---

## File Structure

- `app/storage.py`：选择文件、Turso 或拒绝写入；保持 `load_json` / `save_json` 签名。
- `app/turso_store.py`：Turso HTTP 客户端，只负责一张 `documents` 表。
- `app/daily_admin.py`：家庭口令的哈希、代数和 cookie 签发。
- `app/play_gate.py`：判断一条请求要不要口令，以及 `next` 是否安全。
- `app/main.py`：健康检查、上传拒绝、口令接口、受保护路由的中间件。
- `web/play-gate.html`：口令输入页。
- `web/admin.html`：管理页增加「家庭口令」。
- `index.py`、`vercel.json`、`.python-version`：Vercel 入口。
- `tests/test_storage_backend.py`、`tests/test_turso_store.py`、`tests/test_play_gate.py`：新测试。

---

### Task 1: 存储入口仍走文件，并留出失败类型

**Files:**
- Modify: `app/storage.py`
- Test: `tests/test_storage_backend.py`

**Interfaces:**
- Consumes: 现有 `DATA_DIR`，测试通过 `monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)` 隔离。
- Produces: `StorageError`；`load_json(name: str, default: dict) -> dict`；`save_json(name: str, data: dict) -> None`；`turso_configured() -> bool`；`health() -> dict`，键为 `storage` 和 `ready`。

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from app.storage import StorageError, health, load_json, save_json, turso_configured


def test_file_roundtrip(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    save_json("scores.json", {"version": 1, "entries": []})
    assert load_json("scores.json", {})["version"] == 1
    assert json.loads((tmp_path / "scores.json").read_text(encoding="utf-8"))["version"] == 1


def test_corrupt_file_returns_default(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    (tmp_path / "scores.json").write_text("{", encoding="utf-8")
    assert load_json("scores.json", {"version": 1}) == {"version": 1}


def test_vercel_without_turso_refuses_writes(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    assert turso_configured() is False
    assert health() == {"storage": "turso", "ready": False}
    with pytest.raises(StorageError):
        save_json("scores.json", {"version": 1})
    assert not (tmp_path / "scores.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_storage_backend.py -v`

Expected: FAIL，`StorageError` 或 `health` 还不存在。

- [ ] **Step 3: Write minimal implementation**

把 `app/storage.py` 改成：

```python
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


class StorageError(RuntimeError):
    pass


def turso_configured() -> bool:
    return bool(os.environ.get("TURSO_DATABASE_URL", "").strip())


def _on_vercel() -> bool:
    return bool(os.environ.get("VERCEL", "").strip())


def health() -> Dict[str, Any]:
    if turso_configured():
        return {"storage": "turso", "ready": False}
    if _on_vercel():
        return {"storage": "turso", "ready": False}
    return {"storage": "file", "ready": True}


def data_path(name: str) -> Path:
    return DATA_DIR / name


def load_json(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if turso_configured() or _on_vercel():
        raise StorageError("暂时存不上")
    path = data_path(name)
    if not path.is_file():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return dict(default)


def save_json(name: str, data: Dict[str, Any]) -> None:
    if turso_configured() or _on_vercel():
        raise StorageError("暂时存不上")
    path = data_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
```

这一步还没有真正连 Turso。配了地址时先拒绝，Task 2 再接上。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_storage_backend.py tests/test_scores.py tests/test_daily_admin.py -v`

Expected: PASS。现有测试没有 `VERCEL` 和 `TURSO_DATABASE_URL`，仍走文件。

- [ ] **Step 5: Commit**

```bash
git add app/storage.py tests/test_storage_backend.py
git commit -m "feat(storage): keep file JSON and refuse ephemeral Vercel writes"
```

---

### Task 2: Turso 文档读写

**Files:**
- Create: `app/turso_store.py`
- Modify: `app/storage.py`
- Test: `tests/test_turso_store.py`

**Interfaces:**
- Consumes: `StorageError`。
- Produces: `TursoStore(database_url: str, auth_token: str, client: httpx.Client | None = None)`，方法 `load(name, default) -> dict`、`save(name, data) -> None`、`ping() -> None`。`health()` 在 Turso 可连通时返回 `{"storage": "turso", "ready": True}`。

- [ ] **Step 1: Write the failing test**

```python
import json

import httpx
import pytest

from app.storage import health, load_json, save_json
from app.turso_store import TursoStore, pipeline_url


def test_pipeline_url_accepts_libsql_scheme():
    assert pipeline_url("libsql://box-org.turso.io") == "https://box-org.turso.io/v2/pipeline"


def test_mock_turso_roundtrip(monkeypatch):
    rows = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer token"
        body = json.loads(request.content.decode())
        results = []
        for item in body["requests"]:
            if item["type"] == "close":
                results.append({"type": "ok", "response": {"type": "close"}})
                continue
            sql = item["stmt"]["sql"]
            args = [a["value"] for a in item["stmt"].get("args") or []]
            if sql.startswith("SELECT body"):
                value = rows.get(args[0])
                row = [[{"type": "text", "value": value}]] if value is not None else []
                results.append({"type": "ok", "response": {"type": "execute", "result": {"rows": row}}})
            elif sql.startswith("INSERT"):
                rows[args[0]] = args[1]
                results.append({"type": "ok", "response": {"type": "execute", "result": {"rows": []}}})
            elif sql.startswith("SELECT 1") or sql.startswith("CREATE"):
                results.append({"type": "ok", "response": {"type": "execute", "result": {"rows": []}}})
            else:
                results.append({"type": "error", "error": {"message": sql}})
        return httpx.Response(200, json={"results": results})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = TursoStore("libsql://box-org.turso.io", "token", client=client)
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://box-org.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")
    monkeypatch.setattr("app.storage._turso_store", lambda: store)

    save_json("scores.json", {"version": 1, "entries": [{"id": "a"}]})
    assert load_json("scores.json", {})["entries"][0]["id"] == "a"
    assert health() == {"storage": "turso", "ready": True}
    client.close()


def test_turso_http_error_raises(monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down")

    store = TursoStore("https://box.turso.io", "token", client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setenv("TURSO_DATABASE_URL", "https://box.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")
    monkeypatch.setattr("app.storage._turso_store", lambda: store)
    with pytest.raises(Exception):
        load_json("scores.json", {"version": 1})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_turso_store.py -v`

Expected: FAIL，`app.turso_store` 不存在。

- [ ] **Step 3: Write minimal implementation**

创建 `app/turso_store.py`：

```python
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from app.storage import StorageError


def pipeline_url(database_url: str) -> str:
    url = database_url.strip()
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://"):]
    url = url.rstrip("/")
    if not url.endswith("/v2/pipeline"):
        url += "/v2/pipeline"
    return url


class TursoStore:
    def __init__(self, database_url: str, auth_token: str, client: Optional[httpx.Client] = None) -> None:
        self._url = pipeline_url(database_url)
        self._token = auth_token
        self._client = client or httpx.Client(timeout=10.0)
        self._ready = False

    def ping(self) -> None:
        self._execute("SELECT 1")

    def load(self, name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        rows = self._execute("SELECT body FROM documents WHERE name = ?", [name])
        if not rows:
            return dict(default)
        raw = rows[0][0]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StorageError("暂时存不上") from exc
        if not isinstance(data, dict):
            raise StorageError("暂时存不上")
        return data

    def save(self, name: str, data: Dict[str, Any]) -> None:
        self._ensure()
        body = json.dumps(data, ensure_ascii=False, indent=2)
        self._execute(
            "INSERT INTO documents (name, body) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET body = excluded.body",
            [name, body],
        )

    def _ensure(self) -> None:
        if self._ready:
            return
        self._execute(
            "CREATE TABLE IF NOT EXISTS documents ("
            "name TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        self._ready = True

    def _execute(self, sql: str, args: Optional[List[str]] = None) -> List[List[str]]:
        stmt: Dict[str, Any] = {"sql": sql}
        if args is not None:
            stmt["args"] = [{"type": "text", "value": item} for item in args]
        payload = {"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]}
        try:
            response = self._client.post(
                self._url,
                headers={"authorization": "Bearer " + self._token},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise StorageError("暂时存不上") from exc
        if response.status_code != 200:
            raise StorageError("暂时存不上")
        parsed = response.json()
        results = parsed.get("results") or []
        if not results or results[0].get("type") != "ok":
            raise StorageError("暂时存不上")
        result = ((results[0].get("response") or {}).get("result") or {})
        rows = []
        for row in result.get("rows") or []:
            rows.append([str(cell.get("value") if isinstance(cell, dict) else cell) for cell in row])
        return rows
```

在 `app/storage.py` 里把 Turso 分支接上。`load_json` / `save_json` 开头改为：

```python
def _turso_store():
    from app.turso_store import TursoStore

    return TursoStore(
        os.environ.get("TURSO_DATABASE_URL", "").strip(),
        os.environ.get("TURSO_AUTH_TOKEN", "").strip(),
    )


def health() -> Dict[str, Any]:
    if turso_configured():
        try:
            _turso_store().ping()
        except StorageError:
            return {"storage": "turso", "ready": False}
        return {"storage": "turso", "ready": True}
    if _on_vercel():
        return {"storage": "turso", "ready": False}
    return {"storage": "file", "ready": True}


def load_json(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if turso_configured():
        return _turso_store().load(name, default)
    if _on_vercel():
        raise StorageError("暂时存不上")
    # 下面保持原来的文件读取
```

`save_json` 同样先处理 Turso 和 Vercel，再写文件。文件损坏时的行为不要改。

测试里的 `pytest.raises(Exception)` 改成 `pytest.raises(StorageError)`，并在 `test_turso_store.py` 顶部导入 `StorageError`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_turso_store.py tests/test_storage_backend.py -v`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add app/turso_store.py app/storage.py tests/test_turso_store.py
git commit -m "feat(storage): store JSON documents in Turso"
```

---

### Task 3: 健康检查和关闭云端上传

**Files:**
- Modify: `app/main.py`（`_health_payload` 与 `admin_games_upload`）
- Test: `tests/test_storage_backend.py`

**Interfaces:**
- Consumes: `health()`、`turso_configured()`、`StorageError`。
- Produces: `/api/v1/health` 增加 `storage`、`ready`；未就绪时 `status` 为 `not_ready`。上传接口在配了 Turso 时返回 400，`detail` 为 `请到家里的管理页上传游戏包`。

- [ ] **Step 1: Write the failing test**

在 `tests/test_storage_backend.py` 追加：

```python
from fastapi.testclient import TestClient

from app.main import app
from helpers import url

client = TestClient(app)


def test_health_reports_file_storage(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    body = client.get(url("/api/v1/health")).json()
    assert body["status"] == "running"
    assert body["storage"] == "file"
    assert body["ready"] is True


def test_upload_rejected_when_turso_configured(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://box.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")
    response = client.post(
        url("/api/v1/admin/games/upload"),
        files={"file": ("game.zip", b"PK", "application/zip")},
        headers={"X-Admin-Token": "nope"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "请到家里的管理页上传游戏包"
```

上传检查要放在管理员校验之前，这样没登录也会得到同一句说明，测试不必先建管理员。

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_storage_backend.py::test_health_reports_file_storage tests/test_storage_backend.py::test_upload_rejected_when_turso_configured -v`

Expected: FAIL，健康检查还没有 `storage`，上传仍返回 401。

- [ ] **Step 3: Write minimal implementation**

`_health_payload` 改为：

```python
def _health_payload() -> Dict[str, Any]:
    from app.storage import health as storage_health

    info = storage_health()
    status = "running" if info["ready"] else "not_ready"
    return {
        "status": status,
        "service": "family_game_box",
        "version": _load_version(),
        "port": 18029,
        "rootPath": get_root_path() or "/",
        "storage": info["storage"],
        "ready": info["ready"],
    }
```

`admin_games_upload` 在读文件之前：

```python
from app.storage import turso_configured

if turso_configured():
    raise HTTPException(status_code=400, detail="请到家里的管理页上传游戏包")
```

增加异常处理，让其他接口的 `StorageError` 变成 503：

```python
from fastapi.responses import JSONResponse
from app.storage import StorageError

@app.exception_handler(StorageError)
async def storage_unavailable(_request: Request, _exc: StorageError):
    return JSONResponse({"detail": "暂时存不上"}, status_code=503)
```

放在 `create_app` 里、`return app` 之前。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_storage_backend.py tests/test_api.py::test_health_ok tests/test_api.py::test_health_alias_unprefixed -v`

Expected: PASS。原健康检查仍返回 `family_game_box`。

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_storage_backend.py
git commit -m "feat(api): report storage health and block cloud game uploads"
```

---

### Task 4: 家庭口令的签发和失效

**Files:**
- Modify: `app/daily_admin.py`
- Modify: `tests/test_daily_admin.py`
- Test: `tests/test_play_gate.py`

**Interfaces:**
- Consumes: `load_json` / `save_json`，文档名 `daily_admin.json`。
- Produces:
  - `admin_status(token) -> dict`，增加 `playGateEnabled: bool`、`hasPlayPassphrase: bool`
  - `put_play_gate(enabled: bool, passphrase: Optional[str]) -> dict`，返回同样这两个字段
  - `issue_play_cookie(passphrase: str, now: Optional[int] = None) -> str`
  - `play_cookie_ok(cookie: Optional[str], now: Optional[int] = None) -> bool`
  - 常量 `PLAY_COOKIE = "fgb_play"`

- [ ] **Step 1: Write the failing test**

`tests/test_daily_admin.py` 里把精确比较改成包含新字段：

```python
assert st == {
    "hasPassword": False,
    "authenticated": False,
    "playGateEnabled": False,
    "hasPlayPassphrase": False,
}
```

新建 `tests/test_play_gate.py`：

```python
import time

import pytest

from app import daily_admin as da


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.DATA_DIR", tmp_path)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)


def test_cannot_enable_without_passphrase():
    with pytest.raises(ValueError):
        da.put_play_gate(True, None)


def test_unlock_and_invalidate_on_change():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    assert da.play_cookie_ok(cookie, now=now) is True
    assert da.play_cookie_ok("bad", now=now) is False
    with pytest.raises(ValueError, match="口令不对"):
        da.issue_play_cookie("nope", now=now)
    da.put_play_gate(True, "family2")
    assert da.play_cookie_ok(cookie, now=now) is False


def test_disable_keeps_generation():
    da.put_play_gate(True, "family")
    now = int(time.time())
    cookie = da.issue_play_cookie("family", now=now)
    first = da._load()["playGeneration"]
    da.put_play_gate(False, None)
    assert da._load()["playGeneration"] == first
    da.put_play_gate(True, None)
    assert da._load()["playGeneration"] == first + 1
    assert da.play_cookie_ok(cookie, now=now) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_play_gate.py tests/test_daily_admin.py::test_setup_login_and_status -v`

Expected: FAIL，`put_play_gate` 不存在，状态里还没有新字段。

- [ ] **Step 3: Write minimal implementation**

在 `app/daily_admin.py` 增加：

```python
import hmac
import time

PLAY_COOKIE = "fgb_play"
PLAY_TTL = 30 * 24 * 3600


def _play_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    data.setdefault("playGateEnabled", False)
    data.setdefault("playPassphraseSalt", "")
    data.setdefault("playPassphraseHash", "")
    data.setdefault("playTokenKey", "")
    data.setdefault("playGeneration", 0)
    return data


def _public_play(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "playGateEnabled": bool(data.get("playGateEnabled")),
        "hasPlayPassphrase": bool(data.get("playPassphraseHash")),
    }
```

`_load` 在返回前调用 `_play_fields`。`admin_status` 的返回值合并 `_public_play(data)`。

```python
def put_play_gate(enabled: bool, passphrase: Optional[str]) -> Dict[str, Any]:
    data = _load()
    passphrase = (passphrase or "").strip()
    changed = False
    if passphrase:
        if len(passphrase) < 4:
            raise ValueError("password too short")
        if not data.get("playTokenKey"):
            data["playTokenKey"] = secrets.token_hex(32)
        data["playPassphraseSalt"] = secrets.token_hex(16)
        data["playPassphraseHash"] = _hash(data["playPassphraseSalt"], passphrase)
        changed = True
    if enabled and not data.get("playPassphraseHash"):
        raise ValueError("passphrase not set")
    turning_on = enabled and not data.get("playGateEnabled")
    if changed or turning_on:
        data["playGeneration"] = int(data.get("playGeneration") or 0) + 1
    data["playGateEnabled"] = bool(enabled)
    _save(data)
    return _public_play(data)


def issue_play_cookie(passphrase: str, now: Optional[int] = None) -> str:
    data = _load()
    if not data.get("playPassphraseHash"):
        raise ValueError("口令不对")
    if _hash(data.get("playPassphraseSalt") or "", passphrase or "") != data["playPassphraseHash"]:
        raise ValueError("口令不对")
    current = int(now if now is not None else time.time())
    exp = current + PLAY_TTL
    payload = "%s.%s" % (int(data["playGeneration"]), exp)
    sig = hmac.new(data["playTokenKey"].encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return payload + "." + sig


def play_cookie_ok(cookie: Optional[str], now: Optional[int] = None) -> bool:
    data = _load()
    if not cookie or not data.get("playTokenKey"):
        return False
    parts = cookie.split(".")
    if len(parts) != 3:
        return False
    payload = parts[0] + "." + parts[1]
    expect = hmac.new(data["playTokenKey"].encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, parts[2]):
        return False
    try:
        generation = int(parts[0])
        exp = int(parts[1])
    except ValueError:
        return False
    current = int(now if now is not None else time.time())
    return generation == int(data.get("playGeneration") or 0) and current <= exp
```

同一次保存只加一次代数：新口令，或者从关到开，满足任一即加 1。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_play_gate.py tests/test_daily_admin.py -v`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add app/daily_admin.py tests/test_daily_admin.py tests/test_play_gate.py
git commit -m "feat(admin): store a separate family play passphrase"
```

---

### Task 5: 口令挡住游戏和成绩

**Files:**
- Create: `app/play_gate.py`
- Modify: `app/main.py`
- Create: `web/play-gate.html`
- Test: `tests/test_play_gate.py`

**Interfaces:**
- Consumes: `put_play_gate`、`issue_play_cookie`、`play_cookie_ok`、`PLAY_COOKIE`、`require_admin`、`with_root`。
- Produces: `needs_play(method: str, path: str) -> bool`；`safe_next(raw: str) -> str`。`GET /api/v1/play-gate` 返回 `{enabled, unlocked}`。`POST /api/v1/play-gate/unlock` 成功时设置 cookie。`PUT /api/v1/admin/play-gate` 需要管理员。

- [ ] **Step 1: Write the failing test**

在 `tests/test_play_gate.py` 追加接口测试。使用 `TestClient`，并给成绩请求带上已注册终端。

```python
import uuid

from fastapi.testclient import TestClient

from helpers import url
from app.main import app

client = TestClient(app)
TERMINAL = str(uuid.uuid4())


def _play_on():
    da.setup_password("secret123")
    token = da.login("secret123")["token"]
    client.put(
        url("/api/v1/admin/play-gate"),
        json={"enabled": True, "passphrase": "family"},
        headers={"X-Admin-Token": token},
    )
    client.post(url("/api/v1/terminals/register"), json={"terminalId": TERMINAL, "nickname": "小明"})
    return token


def test_gate_off_allows_score():
    client.post(url("/api/v1/terminals/register"), json={"terminalId": TERMINAL, "nickname": "小明"})
    response = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers={"X-Terminal-Id": TERMINAL},
    )
    assert response.status_code == 200


def test_gate_on_blocks_score_and_today_until_unlock():
    _play_on()
    headers = {"X-Terminal-Id": TERMINAL}
    blocked = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers=headers,
    )
    assert blocked.status_code == 401
    assert client.get(url("/api/v1/daily/today")).status_code == 401
    assert client.get(url("/api/v1/leaderboard/recent")).status_code == 200
    page = client.get(url("/daily"), follow_redirects=False)
    assert page.status_code == 307
    assert "/play-gate?next=" in page.headers["location"]
    bad = client.post(url("/api/v1/play-gate/unlock"), json={"passphrase": "nope"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "口令不对"
    ok = client.post(url("/api/v1/play-gate/unlock"), json={"passphrase": "family"})
    assert ok.status_code == 200
    unlocked = client.post(
        url("/api/v1/scores"),
        json={"gameId": "stroop", "mode": "challenge", "tier": "normal", "metrics": {"correct": 1, "total": 1, "timeMs": 1000}},
        headers=headers,
    )
    assert unlocked.status_code == 200


def test_safe_next_rejects_external():
    from app.play_gate import safe_next
    from app.root_path import with_root

    assert safe_next("//evil.example") == with_root("/")
    assert safe_next("/daily") == "/daily"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_play_gate.py -v`

Expected: FAIL，路由 404，`app.play_gate` 不存在。

- [ ] **Step 3: Write minimal implementation**

创建 `app/play_gate.py`：

```python
from __future__ import annotations

from urllib.parse import quote

from app.daily_admin import play_cookie_ok, require_admin
from app.root_path import get_root_path, with_root


def safe_next(raw: str) -> str:
    if not raw.startswith("/") or raw.startswith("//"):
        return with_root("/")
    return raw


def _relative(path: str) -> str:
    prefix = get_root_path()
    if prefix and (path == prefix or path.startswith(prefix + "/")):
        path = path[len(prefix):] or "/"
    return path


def needs_play(method: str, path: str) -> bool:
    rel = _relative(path)
    if rel.startswith("/yuwen-daily/leaderboard") or rel.startswith("/daily/leaderboard"):
        return False
    if rel == "/daily" or rel.startswith("/daily/"):
        return True
    if rel == "/yuwen-daily" or rel.startswith("/yuwen-daily/"):
        return True
    if rel == "/games" or rel.startswith("/games/"):
        return True
    if method == "GET" and rel in ("/api/v1/daily/today", "/api/v1/yuwen-daily/today"):
        return True
    if method == "POST" and rel in (
        "/api/v1/scores",
        "/api/v1/daily/runs",
        "/api/v1/yuwen-daily/answer",
        "/api/v1/yuwen-daily/finish",
    ):
        return True
    if method == "PATCH" and rel.startswith("/api/v1/daily/runs/"):
        return True
    return False


def allowed(method: str, path: str, cookie: str | None, admin_token: str | None) -> bool:
    from app.daily_admin import _load

    if not _load().get("playGateEnabled"):
        return True
    if not needs_play(method, path):
        return True
    try:
        require_admin(admin_token)
        return True
    except PermissionError:
        pass
    return play_cookie_ok(cookie)


def gate_location(path: str) -> str:
    return with_root("/play-gate") + "?next=" + quote(safe_next(path), safe="/")
```

在 `create_app` 里，静态文件挂载之后加中间件：

```python
@app.middleware("http")
async def play_gate_middleware(request: Request, call_next):
    from app.play_gate import _relative, allowed, gate_location

    cookie = request.cookies.get("fgb_play")
    admin_token = request.headers.get("x-admin-token")
    if allowed(request.method, request.url.path, cookie, admin_token):
        return await call_next(request)
    if _relative(request.url.path).startswith("/api/"):
        return JSONResponse({"detail": "需要口令"}, status_code=401)
    return RedirectResponse(gate_location(request.url.path), status_code=307)
```

注册路由：

```python
class PlayUnlockBody(BaseModel):
    passphrase: str = Field(min_length=1, max_length=128)


class PlayGateBody(BaseModel):
    enabled: bool
    passphrase: Optional[str] = None


@api.get("/api/v1/play-gate")
async def play_gate_state(request: Request):
    from app.daily_admin import _load, play_cookie_ok

    data = _load()
    enabled = bool(data.get("playGateEnabled"))
    unlocked = (not enabled) or play_cookie_ok(request.cookies.get("fgb_play"))
    return {"enabled": enabled, "unlocked": unlocked}


@api.post("/api/v1/play-gate/unlock")
async def play_gate_unlock(body: PlayUnlockBody):
    from app.daily_admin import PLAY_COOKIE, issue_play_cookie

    try:
        value = issue_play_cookie(body.passphrase)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="口令不对") from exc
    response = JSONResponse({"ok": True})
    response.set_cookie(
        PLAY_COOKIE,
        value,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=False,
        path=get_root_path() or "/",
    )
    return response


@api.put("/api/v1/admin/play-gate")
async def admin_play_gate(body: PlayGateBody, x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
    try:
        daily_admin_mod.require_admin(x_admin_token)
        return daily_admin_mod.put_play_gate(body.enabled, body.passphrase)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api.get("/play-gate")
async def play_gate_page():
    page = WEB_DIR / "play-gate.html"
    if page.is_file():
        return FileResponse(page, media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=404, detail="play-gate.html missing")
```

解锁接口要按当前请求决定 `Secure`。把 `play_gate_unlock` 加上 `request: Request`，`secure=request.url.scheme == "https"`。

`web/play-gate.html` 使用现有主题，表单调用 `fetch("/api/v1/play-gate/unlock")`。家里的 HTML 前缀中间件会给这个绝对路径加上 `/game-box`。成功后跳到 `next` 查询参数；参数不合法就去 `/`。错误时页面显示返回 JSON 里的 `detail`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_play_gate.py tests/test_daily_api.py tests/test_scores.py -v`

Expected: PASS。开关默认关闭，原有成绩和每日挑战测试仍能提交。

- [ ] **Step 5: Commit**

```bash
git add app/play_gate.py app/main.py web/play-gate.html tests/test_play_gate.py
git commit -m "feat(play): require the family passphrase when the gate is on"
```

---

### Task 6: 管理页设置口令

**Files:**
- Modify: `web/admin.html`
- Test: `tests/test_daily_api.py`

**Interfaces:**
- Consumes: `PUT /api/v1/admin/play-gate`，`GET /api/v1/admin/status` 的 `playGateEnabled` 和 `hasPlayPassphrase`。页面里的 `api()` 和 `token()`。
- Produces: 管理页标签「家庭口令」。

- [ ] **Step 1: Write the failing test**

在 `tests/test_daily_api.py` 的页面断言旁追加：

```python
def test_admin_page_has_play_gate():
    admin = client.get(url("/admin")).text
    assert "家庭口令" in admin
    assert "开启家庭口令" in admin
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_daily_api.py::test_admin_page_has_play_gate -v`

Expected: FAIL，页面里还没有这两句。

- [ ] **Step 3: Write minimal implementation**

在 `#main-tabs` 增加按钮：

```html
<button type="button" data-tab="gate">家庭口令</button>
```

在 `#tab-diff` 后增加面板：

```html
<div id="tab-gate" class="hidden">
  <div class="card">
    <h2>家庭口令</h2>
    <p class="meta">打开后，进入游戏和每日挑战需要口令。大厅和排行榜仍可查看。管理员密码不能用来玩游戏。</p>
    <div class="err" id="gate-err"></div>
    <label><input id="gate-enabled" type="checkbox"> 开启家庭口令</label>
    <label for="gate-pass">设置或更换口令</label>
    <input id="gate-pass" type="password" autocomplete="new-password">
    <button type="button" id="btn-save-gate">保存</button>
  </div>
</div>
```

`switchTab` 里对 `tab-gate` 做同样的 `hidden` 切换，并在 `name === "gate"` 时调用 `loadPlayGate()`。

```javascript
function loadPlayGate() {
  api("/api/v1/admin/status", { headers: { "X-Admin-Token": token() } }).then(function (st) {
    document.getElementById("gate-enabled").checked = !!st.playGateEnabled;
  });
}

document.getElementById("btn-save-gate").addEventListener("click", function () {
  var err = document.getElementById("gate-err");
  err.textContent = "";
  var body = { enabled: document.getElementById("gate-enabled").checked };
  var pass = document.getElementById("gate-pass").value;
  if (pass) body.passphrase = pass;
  api("/api/v1/admin/play-gate", { method: "PUT", admin: true, body: body }).then(function () {
    document.getElementById("gate-pass").value = "";
    err.textContent = "已保存";
  }).catch(function (ex) {
    err.textContent = ex.message || "保存失败";
  });
});
```

`api()` 使用 `opts.body`，上面的调用已经按这个字段写好。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_daily_api.py::test_admin_page_has_play_gate tests/test_daily_api.py::test_admin_setup_template_regenerate -v`

Expected: PASS。原有「管理」「挑战模板」断言还在。

- [ ] **Step 5: Commit**

```bash
git add web/admin.html tests/test_daily_api.py
git commit -m "feat(admin): add the family passphrase switch to the admin page"
```

---

### Task 7: Vercel 入口

**Files:**
- Create: `index.py`
- Create: `vercel.json`
- Create: `.python-version`
- Modify: `family-product.json` 的 `validateFiles` 不加入这些文件。家里的 zip 校验保持原样。

**Interfaces:**
- Consumes: `app.main:app`。
- Produces: Vercel 能识别的 Python 入口。生产环境变量由人在 Vercel 项目里设置，不写进仓库。

- [ ] **Step 1: Write the failing test**

```python
def test_vercel_entry_exports_app():
    import index
    from app.main import app

    assert index.app is app
```

放进 `tests/test_storage_backend.py`。

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_storage_backend.py::test_vercel_entry_exports_app -v`

Expected: FAIL，`index` 模块不存在。

- [ ] **Step 3: Write minimal implementation**

`index.py`：

```python
"""Vercel Python entry. Set ROOT_PATH empty, plus TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.

Preview 使用单独的 Turso 数据库，不要填生产库的地址。
"""

from app.main import app

__all__ = ["app"]
```

`vercel.json`：

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "index.py": {
      "maxDuration": 30
    }
  }
}
```

`.python-version` 的内容是一行 `3.12`。

仓库里不要写 Turso 地址和 token。Vercel 项目里生产环境设置 `ROOT_PATH` 为空、`TURSO_DATABASE_URL`、`TURSO_AUTH_TOKEN`。Preview 环境设置另一组 Turso 变量。Git 仓库接入后，生产分支选 `main`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_storage_backend.py tests/test_play_gate.py -v`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add index.py vercel.json .python-version tests/test_storage_backend.py
git commit -m "feat(deploy): add a Vercel entry for the game box"
```

---

## Self-Review

规格里的家里 JSON、Turso 行、健康检查、上传拒绝、口令开关、cookie 失效、受保护路由、管理页、Vercel 入口和 Preview 分库，都有对应任务。

没有把排行改成按表查询，也没有给家庭成员做账号。

`put_play_gate`、`issue_play_cookie`、`play_cookie_ok`、`needs_play`、`safe_next` 在前后任务里的名字一致。更换口令只增加一次代数，避免和「从关到开」叠成两次。
