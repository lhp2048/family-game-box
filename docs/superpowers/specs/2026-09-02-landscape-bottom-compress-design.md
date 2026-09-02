# 横屏/每日挑战对局区过小

**日期:** 2026-09-02  
**状态:** 已落地（截图确认根因后修订）  
**产品:** family_game_box

## 1. 目标

每日挑战对局时，游戏区被挤在上方一小块，下方大片空白；横屏更严重。让 iframe 吃满剩余视口，对局控件变大。

## 2. 根因（截图）

不是底栏按钮「盖住」棋盘，而是：

1. 壳层顶栏 + HUD 占高，`.fgb-frame` 未用 flex 吃满剩余高度时，观感像底下空一截  
2. iframe 内 24 点：长 tip + 自有 topbar + 四叶盘上限约 300px 顶对齐，下方空白

## 3. 方案

| 处 | 改动 |
|----|------|
| `web/css/fgb-theme.css` | `body.fgb-daily-playing`：对局中隐藏顶栏，`#play`/`.fgb-frame` flex 铺满 `100dvh` |
| `web/daily.html` | `show('play')` 时给 body 加 `fgb-daily-playing` |
| `games/common/game_common.py` DAILY_HEAD | 闯关内隐藏 play topbar / tip，收紧 `.wrap` |
| `games/24points/generate_play.py` | 每日模式放大 clover（约 `62dvh`） |

附带：矮视口下共用 `.actions` 压矮；数独横屏工具行+退出行合成一行（仍保留）。

## 4. 成功标准

- 每日挑战 24 点：四叶盘明显变大，运算符行无需大段下滚即可看到  
- 对局中壳顶栏不占位；退出仍用 HUD「退出」  
- 竖屏单独玩（非每日）布局基本不变
