# 家庭游戏盒 — Vercel 部署与 Turso 存储

**日期:** 2026-10-18  
**状态:** 已确认  
**范围:** 同一套 FastAPI 同时支持家里 zip 安装和 Vercel 发布；持久数据在 Vercel 上写入 Turso；管理页可开关家庭口令

---

## 1. 目标

家里继续用现在的 zip 安装，数据仍写本机 JSON。再增加一条公网路径：GitHub 的 `main` 推送后由 Vercel 发布同一套程序，成绩、挑战和管理配置写入 Turso。

管理员可以打开家庭口令。打开后，玩游戏和提交成绩要先填口令。大厅和排行榜保持可看。

本期不做：

- 替换家里的门户 zip 安装
- 把计分、出卷、排行改写成按表查询
- 在 Vercel 上上传或保存新的游戏包
- 把题库、页面、脚本放进数据库
- 为每个家庭成员单独建账号

---

## 2. 部署

两边跑同一个 `app.main:app`。

| | 家里 | Vercel |
|----|------|--------|
| 发布 | `scripts/build_and_pack.sh` 打 zip，本机或门户安装 | GitHub 仓库接入 Vercel，生产分支 `main`，推送即发布 |
| 入口 | 现有默认 `ROOT_PATH=/game-box`，端口 18029 | `ROOT_PATH` 为空或 `/`，站点在域名根路径 |
| 数据 | 未设置 `TURSO_DATABASE_URL`，写 `data/*.json` | 设置 `TURSO_DATABASE_URL` 和 `TURSO_AUTH_TOKEN` |
| 静态文件 | 安装目录里的 `web/` | 随该次部署带上的 `web/`，含题库和游戏脚本 |
| 游戏包上传 | 管理页保持可用 | 关闭，提示到家里的管理页操作 |

Preview 部署使用另一份 Turso 数据库，不写生产库。

健康检查在配了 Turso 地址时报告 `storage: "turso"`。能连上则为就绪；连不上则为未就绪。未配地址时报告 `storage: "file"`，行为与现在一致。Vercel 上如果没有 Turso 地址，健康检查为未就绪，接口不得把数据写到临时磁盘。

---

## 3. 存储

业务代码继续调用 `load_json` / `save_json`，仍以整份 JSON 文档为单位。切换只发生在这一层：

- 没有 `TURSO_DATABASE_URL`：读写 `data/<name>`，损坏或读失败时返回调用方给的默认值。
- 有该地址：读写 Turso。表为 `documents(name TEXT PRIMARY KEY, body TEXT NOT NULL)`，`name` 是现有文件名，`body` 是这份 JSON 的文本。缺行时返回默认值。写入是整行替换。Turso 报错时向上抛出，接口返回 503，不得用空文档代替。

经过这层的现有文档包括 `scores.json`、`daily_runs.json`、`daily_challenges.json`、`yuwen_daily_runs.json`、`daily_admin.json`、`difficulty.json`、`terminals.json`、`games_registry.json`。题库 `web/games/yuwen/questions.json` 仍从部署文件读取。

并发与现在的文件相同：后写入的整份文档生效。单行替换不会写出半份 JSON。

家里和 Vercel 的配置、成绩互不相通。一边打开家庭口令，不影响另一边。

---

## 4. 家庭口令

口令存在 `daily_admin.json` 这份文档里，和成绩走同一套存储。字段：

- `playGateEnabled`：布尔，默认 `false`
- `playPassphraseSalt`、`playPassphraseHash`：只存盐和 SHA-256，规则与管理员密码相同，最短 4 个字符
- `playTokenKey`：随机签名密钥，首次设置口令时生成
- `playGeneration`：整数，从 0 起

接口不返回口令原文、哈希或签名密钥。

管理页在管理员登录后增加两项：是否开启家庭口令，以及设置或更换口令。请求沿用 `X-Admin-Token`。

- `GET /api/v1/admin/status` 增加 `playGateEnabled`、`hasPlayPassphrase`。
- `PUT /api/v1/admin/play-gate`，正文 `{ "enabled": true/false, "passphrase": "可选" }`。
- 尚未设置口令时把 `enabled` 设为 true，返回 400。
- 正文里带了新口令就更换哈希，并把 `playGeneration` 加 1。
- 从关闭变为打开时，`playGeneration` 加 1。只关闭不加。

玩家：

- `GET /api/v1/play-gate` 返回 `{ "enabled", "unlocked" }`。
- `POST /api/v1/play-gate/unlock`，正文 `{ "passphrase" }`。正确时种下 cookie `fgb_play`，有效期 30 天。错误时返回 401，正文说明为「口令不对」，不种 cookie。

cookie 的值是 `playGeneration`、过期时间，以及用 `playTokenKey` 做的 HMAC-SHA256，不含口令。`Max-Age` 为 30 天，`SameSite=Lax`。HTTPS 上加 `Secure`，家里的 HTTP 不加，这样局域网仍能用。每台浏览器各自持有 cookie。

未解锁时访问受保护页面，重定向到 `/play-gate?next=<原来的路径>`。`/play-gate` 本身不需要口令。口令正确后回到 `next`；`next` 只接受以 `/` 开头、且不是 `//` 的站内路径，否则回到大厅。

开关关闭时忽略 cookie，进游戏和交成绩与现在一样。

开关打开时，下面这些请求必须带有效且代数匹配的 cookie。有效的 `X-Admin-Token` 同样放行，避免管理页读取今日挑战被挡住：

- 页面：`/daily`、`/yuwen-daily`、`/games` 及其下的页面和资源
- 写操作：`POST /api/v1/scores`、`POST /api/v1/daily/runs`、`PATCH /api/v1/daily/runs/{run_id}`、`POST /api/v1/yuwen-daily/answer`、`POST /api/v1/yuwen-daily/finish`
- 题目：`GET /api/v1/daily/today`、`GET /api/v1/yuwen-daily/today`

没有凭证或凭证已失效时，页面重定向到 `/play-gate`，接口返回 401。已有成绩保留。

这些保持开放：大厅 `/`、`/play-gate`、排行榜页面，以及 `GET /api/v1/leaderboard`、`/api/v1/leaderboard/recent`、`/api/v1/leaderboard/global`、`/api/v1/daily/leaderboard`、`/api/v1/yuwen-daily/leaderboard`、`/api/v1/scores/me/bests`、`/api/v1/lobby/summary`。终端注册、健康检查、游戏列表、管理页及其余管理接口也保持开放。

直接输入游戏或挑战地址时同样要先过口令，不能绕过页面。

---

## 5. 失败表现

- 口令错误：提示「口令不对」，不开始本局，不写入成绩。
- 凭证过期，或口令已更换，或关闭后再次打开：退回口令输入。已保存的成绩还在。
- 开关关闭：有没有 cookie 都能玩。
- 家里的 JSON 损坏：仍返回该接口的默认空数据。
- Turso 不可用：成绩和挑战接口返回 503，页面提示暂时存不上。不得把空榜写回去。
- Vercel 未配置 Turso：健康检查未就绪，不把数据写进临时磁盘。
- 在 Vercel 上上传游戏包：拒绝，并说明请到家里的管理页操作。

---

## 6. 验收

现有测试继续使用本地 JSON，家里这条路径全部通过。

新增测试：

- 开关关闭时可以提交成绩。
- 开关打开后，没有凭证不能提交成绩，也不能取到今日题目。
- 口令正确后可以提交成绩。
- 口令错误时返回「口令不对」，成绩不变。
- 更换口令，或关闭后再打开，旧 cookie 失效。
- 大厅和排行榜读取在口令打开时仍成功。
- 用测试 Turso 库写入并读回排行和每日挑战，内容与写入的一致。
- 配了 Turso 地址时，上传游戏包被拒绝。

页面上确认：大厅和排行榜不要求口令；口令打开后，点进游戏或每日挑战才出现口令输入。
