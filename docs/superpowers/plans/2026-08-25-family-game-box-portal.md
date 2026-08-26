# Family Game Box Portal Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `family_game_box` 做成可局域网访问的 FastAPI python-service（:18029），带大厅两卡（24 点挑战 / 舒尔特挑战占位），并打 zip 接入门户安装升级。

**Architecture:** 对齐 `family_cart` 的部署脚本与打包流程；应用入口为 `app.main:app`，静态站目录为 `web/`（构建进 `dist/web/`）。24 点页继续由现有 `generate_*.py` 生成到 `web/games/24points/`。

**Tech Stack:** Python 3.10+、FastAPI、uvicorn、pytest、stdlib 静态 HTML；Windows 优先（`localdevs.txt` 中的 Python）；部署脚本三端（bat/sh）从 cart 拷贝改名。

**Spec:** `family_game_box/docs/superpowers/specs/2026-08-25-family-game-box-portal-design.md`

## Global Constraints

- 产品 id：`family_game_box`；端口：`18029`；`packageType`：`python-service`
- health：`GET /api/v1/health`；大厅卡片文案固定为「24 点挑战」「舒尔特挑战」
- 本期不做：舒尔特玩法、Skill/MCP、datacenter 成绩同步
- C++ 规范不适用于本项目；Python 可用 3.10+ 语法
- 仅在用户明确要求时 git commit；实现时若计划含 commit 步骤且用户未要求，跳过 commit

---

## File map（将创建 / 修改）

| 路径 | 职责 |
|------|------|
| `family_game_box/family-product.json` | 门户 manifest |
| `family_game_box/requirements.txt` | fastapi / uvicorn / pytest |
| `family_game_box/app/__init__.py` | 包标记 |
| `family_game_box/app/main.py` | FastAPI：health、games、静态挂载 |
| `family_game_box/app/games_catalog.py` | `/api/v1/games` 数据 |
| `family_game_box/web/index.html` | 大厅 |
| `family_game_box/web/games/schulte/index.html` | 舒尔特占位 |
| `family_game_box/tests/test_api.py` | HTTP 契约测试 |
| `family_game_box/deploy/**` | 从 cart 拷贝并改端口/模块路径 |
| `family_game_box/scripts/build.bat` 等 | 生成游戏页 + 组装 dist + pack |
| `docs/FAMILY_PACKAGING.md`、`REQ.txt`、`local.env` | 登记新产品 |
| `family_smart_center_web/public/marketing.html`、`js/marketing.js` | 产品中心卡片 |

---

### Task 1: Manifest + 依赖 + FastAPI health

**Files:**
- Create: `family_game_box/family-product.json`
- Create: `family_game_box/requirements.txt`
- Create: `family_game_box/app/__init__.py`
- Create: `family_game_box/app/main.py`
- Create: `family_game_box/tests/test_api.py`
- Create: `family_game_box/pytest.ini`

**Interfaces:**
- Consumes: 无
- Produces: ASGI `app` in `app.main`; `GET /api/v1/health` → JSON with keys `status`, `service`, `version`, `port`

- [ ] **Step 1: 写失败测试**

创建 `family_game_box/pytest.ini`：

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

创建 `family_game_box/tests/test_api.py`：

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    data = body.get("data", body)
    assert data["service"] == "family_game_box"
    assert data["port"] == 18029
    assert data["status"] == "running"
```

- [ ] **Step 2: 跑测试确认失败**

```bat
cd /d d:\Users\mx\Desktop\smart-family\family_game_box
"C:\Program Files\Python\Python312\python.exe" -m pip install fastapi uvicorn pytest httpx -q
"C:\Program Files\Python\Python312\python.exe" -m pytest tests\test_api.py::test_health_ok -v
```

Expected: FAIL（`app.main` 不存在或 import 失败）

- [ ] **Step 3: 实现 manifest、requirements、minimal app**

`family_game_box/family-product.json`：

```json
{
  "manifestVersion": 1,
  "id": "family_game_box",
  "title": "家庭游戏盒",
  "subtitle": "家用小游戏在线网站",
  "version": "0.1.0",
  "port": 18029,
  "defaultInstallDir": "~/family_game_box",
  "zipNameHint": "family_game_box.zip",
  "packageType": "python-service",
  "monorepoPath": "family_game_box",
  "validateFiles": [
    "app/main.py",
    "web/index.html",
    "requirements.txt",
    "family-product.json",
    "INSTALL.txt",
    "install.bat",
    "install.sh",
    "service.bat",
    "service.sh"
  ],
  "healthPath": "/api/v1/health",
  "endpoints": {
    "apiBasePath": "/api/v1",
    "healthPath": "/api/v1/health",
    "webPath": "/"
  },
  "build": {
    "windows": "scripts\\build_and_pack.bat",
    "mac": "./scripts/build_and_pack.sh",
    "linux": "./scripts/build_and_pack.sh",
    "notes": "解压后 install.bat|install.sh 或 service.bat|service.sh <action>"
  },
  "platforms": {
    "darwin": { "serviceScript": "service.sh" },
    "linux": { "serviceScript": "service.sh" },
    "windows": { "serviceScript": "service.bat" }
  }
}
```

`family_game_box/requirements.txt`：

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
httpx>=0.27.0
pytest>=8.0.0
```

`family_game_box/app/__init__.py`：空文件。

`family_game_box/app/main.py`：

```python
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
MANIFEST_PATH = ROOT / "family-product.json"


def _load_version() -> str:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return str(data.get("version") or "0.0.0")
    except OSError:
        return "0.0.0"


app = FastAPI(title="家庭游戏盒", version=_load_version())


@app.get("/api/v1/health")
async def health():
    return {
        "status": "running",
        "service": "family_game_box",
        "version": _load_version(),
        "port": 18029,
    }


@app.get("/")
async def lobby():
    index = WEB_DIR / "index.html"
    if index.is_file():
        return FileResponse(index, media_type="text/html; charset=utf-8")
    return JSONResponse({"service": "family_game_box", "hint": "web/index.html missing"}, status_code=503)


if WEB_DIR.is_dir():
    app.mount("/games", StaticFiles(directory=str(WEB_DIR / "games"), html=True), name="games")
```

临时创建最小 `web/index.html`（Task 3 会替换），使 `/` 不 503：

```html
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>家庭游戏盒</title></head>
<body><h1>家庭游戏盒</h1></body></html>
```

- [ ] **Step 4: 再跑 health 测试**

```bat
cd /d d:\Users\mx\Desktop\smart-family\family_game_box
"C:\Program Files\Python\Python312\python.exe" -m pytest tests\test_api.py::test_health_ok -v
```

Expected: PASS。若测试期望 `data` 包装而实现是扁平 JSON，则把断言改成扁平（与本 Task 实现一致，不要引入 cart 的 `success()` 包装）。

- [ ] **Step 5: Commit（仅当用户要求）**

```bash
git add family_game_box/family-product.json family_game_box/requirements.txt family_game_box/app family_game_box/tests family_game_box/pytest.ini family_game_box/web/index.html
git commit -m "feat(game_box): add FastAPI health skeleton and manifest"
```

---

### Task 2: `/api/v1/games` 目录 API

**Files:**
- Create: `family_game_box/app/games_catalog.py`
- Modify: `family_game_box/app/main.py`
- Modify: `family_game_box/tests/test_api.py`

**Interfaces:**
- Consumes: Task 1 `app`
- Produces: `GET /api/v1/games` → `{"games":[...]}`；条目字段 `id`,`title`,`status`,`path`；24points 另有 `extra.library`

- [ ] **Step 1: 扩展失败测试**

在 `tests/test_api.py` 追加：

```python
def test_games_catalog():
    r = client.get("/api/v1/games")
    assert r.status_code == 200
    games = r.json()["games"]
    assert [g["id"] for g in games] == ["24points", "schulte"]
    assert games[0]["title"] == "24 点挑战"
    assert games[0]["status"] == "ready"
    assert games[0]["path"] == "/games/24points/quiz.html"
    assert games[0]["extra"]["library"] == "/games/24points/library.html"
    assert games[1]["title"] == "舒尔特挑战"
    assert games[1]["status"] == "coming_soon"
    assert games[1]["path"] == "/games/schulte/"
```

- [ ] **Step 2: 跑测确认失败**

```bat
"C:\Program Files\Python\Python312\python.exe" -m pytest tests\test_api.py::test_games_catalog -v
```

Expected: FAIL 404

- [ ] **Step 3: 实现 catalog**

`app/games_catalog.py`：

```python
from __future__ import annotations

from typing import Any, Dict, List


def list_games() -> List[Dict[str, Any]]:
    return [
        {
            "id": "24points",
            "title": "24 点挑战",
            "status": "ready",
            "path": "/games/24points/quiz.html",
            "extra": {"library": "/games/24points/library.html"},
        },
        {
            "id": "schulte",
            "title": "舒尔特挑战",
            "status": "coming_soon",
            "path": "/games/schulte/",
        },
    ]
```

在 `app/main.py` 增加：

```python
from app.games_catalog import list_games

@app.get("/api/v1/games")
async def games():
    return {"games": list_games()}
```

- [ ] **Step 4: 跑通测试**

```bat
"C:\Program Files\Python\Python312\python.exe" -m pytest tests\test_api.py -v
```

Expected: PASS

---

### Task 3: 大厅页 + 舒尔特占位

**Files:**
- Modify: `family_game_box/web/index.html`
- Create: `family_game_box/web/games/schulte/index.html`
- Modify: `family_game_box/tests/test_api.py`（可选：检查 `/` 含两卡文案）

**Interfaces:**
- Consumes: `/api/v1/games`（大厅 JS 拉取；失败时 HTML 内已有两卡兜底）
- Produces: 浏览器打开 `/` 可见两卡标题

- [ ] **Step 1: 写大厅 HTML**

`web/index.html` 要求：

- `<title>家庭游戏盒</title>`
- `h1` 文案「家庭游戏盒」
- 两张卡：`data-game-id="24points"` / `data-game-id="schulte"`，标题「24 点挑战」「舒尔特挑战」
- 24 点卡主链 `/games/24points/quiz.html`，次要「解法库」→ `/games/24points/library.html`
- 舒尔特卡链 `/games/schulte/`
- 可选：`fetch('/api/v1/games')` 校验/刷新链接；失败仍用静态链接
- 视觉：浅色纸感背景 + 深绿强调（对齐现有 24 点页色调即可，勿套门户 purple）

示例骨架（实现时可润色 CSS，但文案与 `data-game-id` 必须保留）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>家庭游戏盒</title>
<style>
:root { --ink:#1a2421; --muted:#5c6b66; --paper:#f3efe6; --accent:#0f7a5a; }
body { margin:0; font-family:"Segoe UI",system-ui,sans-serif; background:radial-gradient(1200px 600px at 10% -10%,#fff8e8,#f3efe6); color:var(--ink); }
main { max-width:880px; margin:0 auto; padding:48px 20px 64px; }
h1 { font-size:2rem; margin:0 0 8px; }
.lead { color:var(--muted); margin:0 0 32px; }
.grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }
.card { display:block; text-decoration:none; color:inherit; background:rgba(255,252,246,.9); border:1px solid rgba(26,36,33,.12); border-radius:16px; padding:20px; box-shadow:0 18px 50px rgba(26,36,33,.08); }
.card h2 { margin:0 0 8px; font-size:1.25rem; }
.card p { margin:0; color:var(--muted); font-size:.95rem; }
.card .meta { margin-top:12px; color:var(--accent); font-size:.85rem; }
.secondary { display:inline-block; margin-top:10px; color:var(--accent); font-size:.9rem; }
</style>
</head>
<body>
<main>
  <h1>家庭游戏盒</h1>
  <p class="lead">家里的小游戏站，同一 Wi‑Fi 下用浏览器打开即可。</p>
  <div class="grid" id="game-grid">
    <a class="card" data-game-id="24points" href="/games/24points/quiz.html">
      <h2>24 点挑战</h2>
      <p>休闲或计时挑战，练心算与整数四则。</p>
      <div class="meta">可玩</div>
    </a>
    <a class="card" data-game-id="schulte" href="/games/schulte/">
      <h2>舒尔特挑战</h2>
      <p>注意力训练格子挑战。</p>
      <div class="meta">即将上线</div>
    </a>
  </div>
  <a class="secondary" href="/games/24points/library.html">24 点 · 解法库</a>
</main>
</body>
</html>
```

- [ ] **Step 2: 舒尔特占位页**

`web/games/schulte/index.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>舒尔特挑战 · 即将上线</title>
<style>
body{font-family:"Segoe UI",system-ui,sans-serif;background:#f3efe6;color:#1a2421;margin:0;padding:48px 20px;text-align:center}
a{color:#0f7a5a}
</style>
</head>
<body>
  <h1>舒尔特挑战</h1>
  <p>即将上线，敬请期待。</p>
  <p><a href="/">返回大厅</a></p>
</body>
</html>
```

- [ ] **Step 3: 本地起服务目视检查**

```bat
cd /d d:\Users\mx\Desktop\smart-family\family_game_box
"C:\Program Files\Python\Python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 18029
```

浏览器打开 `http://127.0.0.1:18029/`，确认两卡文案；打开舒尔特见「即将上线」。Ctrl+C 结束。

- [ ] **Step 4: 测试首页含文案**

```python
def test_lobby_html():
    r = client.get("/")
    assert r.status_code == 200
    text = r.text
    assert "24 点挑战" in text
    assert "舒尔特挑战" in text
```

跑全量 `pytest tests -v` → PASS。

---

### Task 4: 24 点产物路径接入 build

**Files:**
- Modify: `family_game_box/scripts/build.bat`
- Modify: `family_game_box/scripts/dev.bat`
- Modify: `family_game_box/scripts/run.bat`
- Modify: `family_game_box/scripts/clean.bat`
- Create: `family_game_box/scripts/build_and_pack.bat`（本 Task 可先只改 build；pack 在 Task 6）

**Interfaces:**
- Consumes: `generate_html.py --dist`、`generate_quiz.py --dist`；`web/` 源文件
- Produces: `dist/` 内含 `app/`、`web/`（含 24points + schulte）、`requirements.txt`、`family-product.json`（完整 dist 组装在 Task 5/6 与 deploy 一起完成；本 Task 至少保证游戏 HTML 生成到正确相对路径）

- [ ] **Step 1: 改 `scripts/build.bat` 生成到 web 游戏目录，并组装完整 dist**

用 `localdevs.txt` 的 Python（`C:\Program Files\Python\Python312\python.exe`）。逻辑：

1. 若无 `output\solutions.txt` → 报错提示 `update_data.bat`
2. 清空并创建 `dist\web\games\24points`、`dist\web\games\schulte`、`dist\app`、`dist\scripts\lib`、`dist\logs`
3. 调用：

```bat
"%PYTHON%" generate_html.py --solutions output\solutions.txt --summary output\summary.txt --out output\index.html --dist dist\web\games\24points\library.html
"%PYTHON%" generate_quiz.py --solutions output\solutions.txt --out output\quiz.html --dist dist\web\games\24points\quiz.html
```

4. `copy web\index.html` → `dist\web\index.html`；`copy web\games\schulte\index.html` → `dist\web\games\schulte\`
5. `xcopy app` → `dist\app`；copy `requirements.txt`、`family-product.json`
6. （deploy 文件在 Task 5 就绪后）copy `deploy\INSTALL.txt` → `dist\INSTALL.txt`；copy `service/install` 与平台脚本到 `dist`（与 cart `scripts\build.bat` 相同结构，但源码目录是 `app` 不是 `src`，静态是 `web` 不是 `static`）
7. 调用门户校验：

```bat
set "PORTAL_SCRIPTS=%ROOT%\..\family_smart_center_web\scripts"
"%PYTHON%" "%PORTAL_SCRIPTS%\validate_manifest.py" "%ROOT%\family-product.json" --dist "%DIST%"
```

若 Task 5 尚未完成，本步可先注释 validate，Task 5 结束后再打开。

- [ ] **Step 2: 跑 build**

```bat
cd /d d:\Users\mx\Desktop\smart-family\family_game_box
scripts\build.bat
```

Expected: `dist\web\games\24points\quiz.html` 与 `library.html` 存在；`dist\web\index.html` 存在。

- [ ] **Step 3: 更新 `dev.bat` / `run.bat`**

`dev.bat`：call build → 用 venv 或系统 Python 在仓库根启动：

```bat
"%PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 18029
```

并打开 Chrome `http://127.0.0.1:18029/`（路径来自 `localdevs.txt`）。

注意：开发时静态来自源码树 `web/`；build 后的 `dist` 用于打包。开发运行应在 **源码根** 起 uvicorn（`app` + `web`），不要 cd 进 dist（除非单独测安装布局）。

`run.bat`：不 build，直接起服务并开浏览器。

`clean.bat`：删除 `dist`、`dist_out`、`release`（若有）。

---

### Task 5: 部署脚本（从 family_cart 拷贝改写）

**Files:**
- Create tree under `family_game_box/deploy/`（windows/linux/mac/lib + INSTALL.txt + service/install）
- Create root `family_game_box/install.bat`、`install.sh`、`service.bat`、`service.sh`（可与 deploy 根脚本相同，或 thin wrapper 调 deploy；对齐 cart：源在 `deploy/`，根目录再各一份 shortcut，build 时只打 dist 根）

**Interfaces:**
- Consumes: `dist` 布局中的 `app.main:app`、`requirements.txt`
- Produces: `service.bat|sh install|start|stop|restart|status|uninstall`；Windows 计划任务名 `FamilyGameBox`；macOS label `com.family.smart.game-box`；默认端口 `18029`

- [ ] **Step 1: 拷贝 cart 部署树**

在 PowerShell：

```powershell
$src = "d:\Users\mx\Desktop\smart-family\family_cart\deploy"
$dst = "d:\Users\mx\Desktop\smart-family\family_game_box\deploy"
Copy-Item -Recurse -Force $src $dst
# 不要 skills 安装脚本：game_box 本期无 skill
```

同时从 cart 根复制 `install.bat`、`install.sh`、`service.bat`、`service.sh` 到 `family_game_box\`（若 cart 根是指向 deploy 的副本，保持同样模式）。

- [ ] **Step 2: 全局替换（必须逐项核对）**

在 `family_game_box/deploy` 与根 `service.*` / `install.*` 内替换：

| 查找 | 替换为 |
|------|--------|
| `18028` | `18029` |
| `FamilyCart` | `FamilyGameBox` |
| `family_cart` | `family_game_box` |
| `family-cart` | `family-game-box` |
| `com.family.smart.cart` | `com.family.smart.game-box` |
| `src.main:app` | `app.main:app` |
| `src\main.py` | `app\main.py` |
| `src/main.py` | `app/main.py` |
| `from src.main import app` | `from app.main import app` |
| `Family Cart` / `电商查券` 等说明文案 | `家庭游戏盒` / 对应说明 |

删除任何 `install-*-skill*` 引用；`INSTALL.txt` 重写为 game_box 说明（端口 18029、health `/api/v1/health`、无 Skill）。

- [ ] **Step 3: 修正 `setup_venv.bat` 探测 import**

确保含：

```bat
"%PY%" -c "import uvicorn; from app.main import app"
```

- [ ] **Step 4: 修正 `run_service.bat`**

```bat
start "" /B "%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
```

默认 `PORT=18029`。

- [ ] **Step 5: 无 .env 依赖**

cart 的 install 会写 `.env` 的 PORT。game_box 可不依赖 `.env`：`run_service.bat` 用环境变量/`set PORT=18029` 即可；若保留写 `.env` 逻辑也无妨，但 `app/main.py` 不需要读 dotenv（端口由 uvicorn CLI 决定）。

- [ ] **Step 6: Linux/mac 脚本同样改 `uvicorn app.main:app` 与 label/unit 名**

核对 `deploy/lib/service_common.sh`、`install_service_mac.sh`、`install_service_linux.sh` 中的服务名与端口。

- [ ] **Step 7: 手工冒烟（源码树）**

```bat
cd /d d:\Users\mx\Desktop\smart-family\family_game_box
REM 先确保 scripts\build.bat 已把 deploy 拷进 dist 后：
cd dist
service.bat install
curl http://127.0.0.1:18029/api/v1/health
service.bat uninstall
```

Expected: health JSON；uninstall 后端口不再 LISTENING。

---

### Task 6: pack + build_and_pack + 校验闭环

**Files:**
- Create: `family_game_box/scripts/pack.bat`
- Create: `family_game_box/scripts/build_and_pack.bat`
- Create: `family_game_box/scripts/build.sh`、`pack.sh`、`build_and_pack.sh`（可后做；Windows 必做）
- Modify: `family_game_box/scripts/build.bat`（确保 validate + 拷贝 deploy 完整）

**Interfaces:**
- Produces: `dist_out/family_game_box.zip`；侧车 `family_game_box.package.json`（由门户 `write_package_info.py` 生成）

- [ ] **Step 1: `pack.bat`**

对齐 cart，但检查 `dist\app\main.py`：

```bat
@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
set "ROOT=%SCRIPT_DIR%.."
set "DIST=%ROOT%\dist"
set "OUT_DIR=%ROOT%\dist_out"
set "PORTAL_SCRIPTS=%ROOT%\..\family_smart_center_web\scripts"

if not exist "%DIST%\app\main.py" (
  echo ERROR: run scripts\build.bat first
  exit /b 1
)

set "PYTHON=python"
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
if exist "C:\Program Files\Python\Python312\python.exe" set "PYTHON=C:\Program Files\Python\Python312\python.exe"

"%PYTHON%" "%PORTAL_SCRIPTS%\bump_manifest_version.py" --manifest "%ROOT%\family-product.json" --dist "%DIST%"
"%PYTHON%" "%PORTAL_SCRIPTS%\validate_manifest.py" "%ROOT%\family-product.json" --dist "%DIST%"
if errorlevel 1 exit /b 1

set "ZIP_NAME=family_game_box.zip"
for /f "usebackq delims=" %%v in (`"%PYTHON%" -c "import json; print(json.load(open(r'%ROOT%\\family-product.json', encoding='utf-8')).get('zipNameHint', 'family_game_box.zip'))"`) do set "ZIP_NAME=%%v"

set "ZIP_FILE=%OUT_DIR%\%ZIP_NAME%"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%"

"%PYTHON%" "%PORTAL_SCRIPTS%\make_zip.py" "%DIST%" "%ZIP_FILE%"
"%PYTHON%" "%PORTAL_SCRIPTS%\write_package_info.py" --manifest "%ROOT%\family-product.json" --zip "%ZIP_FILE%" --dist "%DIST%" --out-dir "%OUT_DIR%"

echo Packed: %ZIP_FILE%
endlocal
```

- [ ] **Step 2: `build_and_pack.bat`**

```bat
@echo off
setlocal
call "%~dp0build.bat"
if errorlevel 1 exit /b 1
call "%~dp0pack.bat"
if errorlevel 1 exit /b 1
endlocal
```

- [ ] **Step 3: 执行打包**

```bat
cd /d d:\Users\mx\Desktop\smart-family\family_game_box
scripts\build_and_pack.bat
dir dist_out\family_game_box.zip
```

Expected: zip 存在且 validate 无 ERROR。

---

### Task 7: 门户展示 + 文档登记

**Files:**
- Modify: `family_smart_center_web/public/marketing.html`
- Modify: `family_smart_center_web/public/js/marketing.js`
- Modify: `family_smart_center_web/server/deploy/service_endpoints.py`（可选 PRODUCT_ENDPOINT_OVERRIDES）
- Modify: `docs/FAMILY_PACKAGING.md` §3 registry
- Modify: `REQ.txt`
- Modify: `local.env`

**Interfaces:**
- 安装后：管理中心通过 install-records + health 展示；产品中心有「家庭游戏盒」卡片可打开 `:18029`

- [ ] **Step 1: marketing 卡片**

在 `marketing.html` 的 `product-showcase-grid` 内、`family_cart` 卡片后追加：

```html
<article class="product-showcase-card" data-product-id="family_game_box">
  <div class="product-showcase-top">
    <span class="product-showcase-icon" aria-hidden="true">🎮</span>
    <div class="product-showcase-title">
      <h3>家庭游戏盒</h3>
      <span class="product-showcase-port">端口 :18029</span>
    </div>
  </div>
  <p class="product-showcase-lead">家用小游戏在线网站，同一 Wi‑Fi 下打开即玩。</p>
  <ul class="product-showcase-list">
    <li>24 点挑战</li>
    <li>舒尔特挑战（即将上线）</li>
    <li>zip 安装，接入家庭中心</li>
  </ul>
  <div class="product-showcase-foot">
    <span class="muted">休闲 · 全家</span>
    <a class="product-open-link hidden" href="#" target="_blank" rel="noopener">打开游戏盒</a>
  </div>
</article>
```

`marketing.js` 的 `PRODUCT_ALIASES` 增加：

```js
family_game_box: ['family_game_box', 'family-game-box'],
```

- [ ] **Step 2: `service_endpoints.py`（可选）**

```python
"family_game_box": {
    "apiBasePath": "/api/v1",
    "healthPath": "/api/v1/health",
    "webPath": "/",
},
```

- [ ] **Step 3: 文档**

`docs/FAMILY_PACKAGING.md` 表格增加一行：

`| family_game_box | family_game_box/ | 18029 | dist_out/family_game_box.zip | scripts\build_and_pack.bat |`

`REQ.txt` 模块一览增加：

`family_game_box 家用小游戏在线网站（FastAPI :18029；大厅：24 点挑战 / 舒尔特挑战）`

`local.env`：

`family_game_box           家用小游戏在线网站（:18029；python-service；大厅两卡）`

- [ ] **Step 4: 端到端验收（人工）**

1. `scripts\build_and_pack.bat`
2. 门户 `http://127.0.0.1:18024/deploy.html` 上传 `dist_out/family_game_box.zip`
3. 安装完成后打开 `http://127.0.0.1:18029/`，两卡可见；24 点可玩；舒尔特占位；health 2xx
4. 对照 spec §8 六条全部勾选

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| python-service :18029 + health | 1 |
| `/api/v1/games` | 2 |
| 大厅两卡文案 | 3 |
| 舒尔特占位 | 3 |
| 24 点路径 quiz/library | 4 |
| deploy service 脚本 | 5 |
| zip + validate | 6 |
| 门户/文档 | 7 |
| 不做 Skill / 舒尔特玩法 | 全篇未实现 |

## Execution Handoff

Plan complete and saved to `family_game_box/docs/superpowers/plans/2026-08-25-family-game-box-portal.md`.

**Two execution options:**

1. **Subagent-Driven（推荐）** — 每 Task 派一个新子代理，Task 间复审  
2. **Inline Execution** — 本会话按 executing-plans 批量推进并设检查点  

选哪一种？
