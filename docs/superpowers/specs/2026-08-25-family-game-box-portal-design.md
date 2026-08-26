# Family Game Box — 大厅 + python-service 门户部署设计

**日期:** 2026-08-25  
**状态:** 已确认  
**范围:** 家用小游戏在线网站骨架、两款入口卡片、zip 上传部署接入家庭中心门户

---

## 1. 目标

将 `family_game_box` 建成可局域网访问的 **python-service**，并与门户 `:18024/deploy.html` 的 zip 安装/升级流程对齐（参考 `family_mediacenter` / `family_cart`）。

本期交付：

- FastAPI 服务（端口 **18029**）+ `/api/v1/health`
- 游戏大厅首页，两张卡片：**24 点挑战**、**舒尔特挑战**
- 舒尔特挑战可玩（3×3～6×6；正序/倒序；休闲/挑战）
- 24 点挑战可玩（沿用现有 play / 解法库）
- `family-product.json` + build/pack + `service.bat|sh`，门户可上传安装

本期不做：Skill / MCP、舒尔特双色变体、账号、排行榜。

---

## 2. 产品标识

| 项 | 值 |
|----|-----|
| 产品 id | `family_game_box` |
| 显示名 | 家庭游戏盒 |
| 副标题 | 家用小游戏在线网站 |
| 端口 | `18029` |
| packageType | `python-service` |
| healthPath | `/api/v1/health` |
| monorepoPath | `family_game_box` |
| zipNameHint | `family_game_box.zip` |
| defaultInstallDir | `~/family_game_box` |
| macOS LaunchAgent | `com.family.smart.game-box` |

---

## 3. 架构

```
浏览器 / 手机
    │  :18029
    ▼
FastAPI (app/main.py)
    ├── GET /api/v1/health
    ├── GET /api/v1/games          （可选：大厅目录 JSON）
    └── StaticFiles → web/
            ├── index.html         大厅
            ├── games/24points/
            │     play.html        24 点挑战
            │     library.html     解法库（现 index.html）
            └── games/schulte/
                  index.html       占位页
```

与媒体中心一致：zip 解压后 `service.* install` 建 `.venv`、注册开机自启、起 uvicorn（或等价 ASGI 入口）。

依赖：Python 3.10+；`fastapi`、`uvicorn`；无下载引擎、无外部 DB。

---

## 4. HTTP 约定

### 4.1 Health

`GET /api/v1/health` → 2xx + JSON，例如：

```json
{
  "status": "running",
  "service": "family_game_box",
  "version": "<from family-product.json>",
  "port": 18029
}
```

### 4.2 大厅与游戏页

| 路径 | 说明 |
|------|------|
| `/` | 大厅：两张卡片 |
| `/games/24points/play.html` | 24 点挑战（可玩） |
| `/games/24points/library.html` | 24 点解法库 |
| `/games/schulte/` 或 `index.html` | 舒尔特挑战占位 |

### 4.3 游戏目录（建议）

`GET /api/v1/games` 返回：

```json
{
  "games": [
    {
      "id": "24points",
      "title": "24 点挑战",
      "status": "ready",
      "path": "/games/24points/play.html",
      "extra": { "library": "/games/24points/library.html" }
    },
    {
      "id": "schulte",
      "title": "舒尔特挑战",
      "status": "coming_soon",
      "path": "/games/schulte/"
    }
  ]
}
```

大厅可用静态写死两张卡；若实现该 API，则优先用 API 渲染（便于后续加游戏）。

---

## 5. 大厅 UI

- 一页一职：标题「家庭游戏盒」+ 一句说明 + **两张卡片**。
- 卡片文案固定：
  1. **24 点挑战** → 进入 play；可附「解法库」次要链接。
  2. **舒尔特挑战** → 进入占位页（「即将上线」），不实现玩法。
- 不出现第三张「更多」空卡。
- 视觉与现有 24 点页风格可统一，但不强制门户 CSS。

---

## 6. 目录与构建

源码侧（示意）：

```
family_game_box/
  app/                     FastAPI
  web/                     大厅与占位源（或由脚本生成进 dist）
  generate_html.py         现有解法库生成
  generate_play.py         现有游玩页生成
  solve_24.py / output/    题库数据
  family-product.json
  deploy/                  INSTALL.txt、service/install、平台脚本
  scripts/                 build / pack / build_and_pack / update_data / clean
  docs/superpowers/...
```

`scripts/build.bat`（及后续 `.sh`）职责：

1. 确保 `output/solutions.txt` 可用（否则提示先 `update_data`）。
2. 生成 24 点 HTML → `dist/web/games/24points/play.html`、`library.html`。
3. 写入/拷贝大厅 `dist/web/index.html`、舒尔特占位 `dist/web/games/schulte/index.html`。
4. 拷贝 `app/`、`family-product.json`、`deploy` 产物（`INSTALL.txt`、`install.*`、`service.*`、`scripts/`）。
5. `validate_manifest.py --dist dist`。

`scripts/pack.bat`：打 `dist_out/family_game_box.zip`，并 `write_package_info.py`。

开发：`scripts/dev.bat` 构建后起本机服务并打开大厅（可用 `localdevs.txt` 中的 Python）。

---

## 7. 门户集成

1. 门户「安装升级」上传 zip → 解析 manifest → 安装到 `defaultInstallDir` → `service install` / `restart`。
2. 管理中心 / 产品中心增加「家庭游戏盒」展示（`:18029`），与已装记录、health 探测合并。
3. 文档更新：
   - `docs/FAMILY_PACKAGING.md` registry 增加一行
   - 根目录 `REQ.txt`、`local.env` 补充端口与职责
4. `portal_catalog` / `marketing` 等是否内置卡片：实现阶段按门户现有「已安装 + 展示」模式接入；至少保证 zip 安装后管理入口可见、可打开。

---

## 8. 验收

| # | 条件 |
|---|------|
| 1 | `scripts\build_and_pack.bat` 产出 `dist_out/family_game_box.zip`，manifest 校验通过 |
| 2 | 门户 deploy 上传安装成功，写入 install-records |
| 3 | `GET http://127.0.0.1:18029/api/v1/health` 为 2xx JSON |
| 4 | 打开 `/` 见「24 点挑战」「舒尔特挑战」两卡 |
| 5 | 24 点挑战可玩；舒尔特为即将上线占位 |
| 6 | `service.bat|sh` 支持 install/start/stop/restart/status/uninstall |

---

## 9. 非目标（再次确认）

- 不实现舒尔特格子玩法与计时逻辑（仅入口 + 占位）
- 不提供 Agent Skill
- 不与 datacenter 同步成绩
- 不改为 static-web（已选定 python-service）
