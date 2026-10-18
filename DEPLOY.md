# 部署到 Vercel（Turso / libSQL）

家庭游戏盒是 FastAPI 应用。Vercel 会识别入口 `app/main.py` 里的 `app`，把整个服务变成一个 Python Function。静态页面仍由应用从 `web/` 提供（`/`、`/js`、`/css`、`/games` 等）。

持久化有两种后端，由环境变量决定：

| 环境 | 行为 |
| --- | --- |
| 未设置 `TURSO_DATABASE_URL` 和 `TURSO_AUTH_TOKEN` | 写入本地 `data/*.json`（现有 install / service 脚本不用改） |
| 两个变量都设置 | 同一批 JSON 文档写入 Turso 表 `kv(name, doc)` |
| 只设置了其中一个 | 读写会报错，避免误以为数据已持久化 |

`name` 与原来的文件名一致，例如 `scores.json`、`terminals.json`、`daily_runs.json`、`daily_challenges.json`、`daily_admin.json`、`difficulty.json`、`games_registry.json`、`yuwen_daily_runs.json`。分数、终端、每日挑战、管理状态、难度都走 `load_json` / `save_json`，因此在 Vercel 上会进 Turso。

## 1. 准备 Turso 数据库

使用 [Turso CLI](https://docs.turso.tech/cli/introduction)（默认引擎是 libSQL，本应用用 Python 包 `libsql` 连接）：

```bash
turso db create family-game-box
turso db show --url family-game-box
turso db tokens create family-game-box
```

`turso db show --url` 的输出类似 `libsql://family-game-box-<org>.turso.io`，作为 `TURSO_DATABASE_URL`。`turso db tokens create` 的输出作为 `TURSO_AUTH_TOKEN`。不要把这两个值写进仓库。

首次读写时应用会执行：

```sql
CREATE TABLE IF NOT EXISTS kv (
  name TEXT PRIMARY KEY NOT NULL,
  doc TEXT NOT NULL
);
```

不需要事先建表。本地 `data/` 不会自动导入；Vercel 上是空库，大厅数据从零开始。

## 2. 在 Vercel 上连接

1. 在 Vercel 导入本仓库。框架应识别为 FastAPI，入口是 `app/main.py`。`vercel.json` 会把 `web/**` 和 `family-product.json` 打进函数包，页面和脚本才能被读到。
2. 打开 Project → Settings → Environment Variables，为 Production（以及需要的 Preview）添加：

| Name | Value |
| --- | --- |
| `TURSO_DATABASE_URL` | `turso db show --url` 的结果 |
| `TURSO_AUTH_TOKEN` | `turso db tokens create` 的结果 |
| `ROOT_PATH` | 可选。不设时站点在 `/game-box/`（与本地安装一致）。设为 `/` 则挂在域名根路径 |

3. 保存后重新部署（环境变量不会作用于已经完成的部署）。
4. 打开健康检查确认存储后端：

- 未改 `ROOT_PATH`：`https://<project>.vercel.app/api/v1/health` 或 `https://<project>.vercel.app/game-box/api/v1/health`
- `ROOT_PATH=/`：`https://<project>.vercel.app/api/v1/health`

期望 JSON 里 `"storage": "turso"`，`"status": "running"`。大厅页面与 `web/js`、`web/css`、已提交的 `web/games/yuwen` 由同一应用提供。

本地验证文件后端时不要导出上述两个变量，然后照常 `./install.sh` 或 `uvicorn app.main:app`。

## 限制

- 管理页上传的游戏包仍写在磁盘 `data/uploaded-games/`。Vercel 函数磁盘是临时的，上传包不会留住。分数、终端、每日、难度、注册表 JSON 会留在 Turso。
- 除语文擂台外，多数内置游戏页由 `scripts/build.sh` 生成，且被 `.gitignore` 排除。仓库里会随 Vercel 部署的是已提交的 `web/` 文件（大厅、管理页、语文擂台）。要带上其他游戏，需要先在本地生成并纳入部署产物。
