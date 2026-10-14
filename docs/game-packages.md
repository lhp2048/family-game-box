# 游戏包装与上传

整盒打包仍用 `./scripts/build_and_pack.sh`，**默认包含全部内置游戏**。  
单游戏可打成 zip，在管理页上传安装；**无需重启服务**。

## 整盒 vs 单游戏

| 方式 | 命令 | 产出 |
|------|------|------|
| 整盒 | `./scripts/build_and_pack.sh` | `dist_out/family_game_box.zip` |
| 单游戏 | `./scripts/pack_game.sh simon` | `dist_out/games/simon.zip` |

## 单游戏 zip 结构

```text
my-puzzle.zip
├── game.json      # 必填
├── index.html     # 或 game.json.entry
├── css/ …
├── js/ …
└── audio/ …       # 可选
```

### `game.json` 示例

```json
{
  "id": "my-puzzle",
  "title": "我的小游戏",
  "subtitle": "一句话说明",
  "entry": "index.html",
  "modes": ["casual", "challenge"],
  "tiers": ["intro", "simple", "normal", "hard", "master", "god"],
  "supportsDaily": true,
  "difficultyDefaults": {
    "intro": { "label": "入门", "trialLimit": 10 },
    "normal": { "label": "普通", "trialLimit": 30 }
  },
  "difficultySchema": [
    { "key": "trialLimit", "type": "number", "label": "试次" },
    { "key": "label", "type": "text", "label": "显示名" }
  ]
}
```

- `id`：小写字母开头，仅 `a-z0-9-`，勿与内置 id 冲突  
- `supportsDaily`：为 true 且**已启用**时，才可出现在每日模板「加关」列表  
- 资源请用**相对路径**；计分调用 `fgbSubmitScore({ gameId, mode, tier, metrics })`，`gameId` 须与 `id` 一致  

## 上传安装（管理员）

1. 打开 `/admin` 登录  
2. 「游戏包」→ 选择 zip → 上传（默认**禁用**）  
3. 点 **启用** → 大厅「自由训练」出现  
4. （可选）「难度参数」调整各档  
5. （可选）若 `supportsDaily`：在「每日挑战」模板中加关 → 保存 → 需要时「重新生成今日挑战」  

上传 / 启用 / 禁用 / 删除均为热更新，**不必重启服务**。

## 每日挑战 checklist（`supportsDaily: true`）

1. 识别 `?daily=1`（可依赖站点 `fgb-daily.js`）  
2. 按 `tier` + `seed` 开可复现的一局  
3. 通关通知父页（`fgbSubmitScore` 或 `FGBDaily.notifyStageDone`）  
4. 退出通知 abort，避免卡死每日页  

## 从内置游戏拆包

```bash
./scripts/pack_game.sh stroop
# → dist_out/games/stroop.zip
```

可将该 zip 上传到另一台已部署的游戏盒做增量更新（同 id 覆盖，已启用状态会保留）。
