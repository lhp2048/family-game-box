# Productized Game Box UI (console shell)

## Direction

Turn the Family Game Box home from a generic “competitive hall” grid into a **living-room game console** experience: bezel framing, HUD stats, spotlight daily tiles, and a horizontal **game library shelf** with cover art and keyboard focus.

## Before (main)

- Title kicker “竞技厅”; flat stat strip + split arena cards + small train grid.
- Games rendered as uniform small cards (`fgb-train-card`) without cover metaphor or shelf navigation.

## After (feat/productized-gamebox-ui)

- **Design tokens** in `web/css/fgb-theme.css`: `--console-*`, focus ring, motion tokens.
- **Console shell** on `web/index.html`: `body.fgb-console`, hero, clock, HUD tiles, spotlight rows, shelf.
- **Components**: `FGBShell.mountTopbar({ console: true })`, `web/js/fgb-home.js` for covers + arrow-key focus.
- Other shell pages keep existing theme; no API changes.

## 数字华容道（`number-slide` MVP）

`/games/number-slide/`：n×n 滑动拼图（4×4 / 5×5 / 6×6 三档），合法滑动洗牌 + seed；排行看 `timeMs` + 步数；`supportsDaily` 可加入专注力挑战模板。

## 心算快答（独立小游戏 `mental-speed`）

`/games/mental-speed/`：即时出题、**每题 3～4 个运算符**（4～5 个数）、连乘积≤100（白名单大数乘例外）、10 题竞速；`fgbSubmitScore` 记总用时。已接入**专注力每日挑战**（`supportsDaily` + `RANKABLE_GAMES`）；单机入口 `/games/mental-speed/` 保留。

## 24 点局内（方案 A）

`games/24points/generate_play.py` → `play.html`：四叶草改为 **2×2 大卡 + 合并后居中排布**；横屏左牌右运算；键盘 `1–4` / `+-*/` / `Z` / `R` / `Esc`；可选「分数中间值」开关。

## Audio clips (Simon / Stroop)

Short MP3 voice/SFX use shared `web/js/fgb-audio-clips.js`: fetch on page load, decode after first gesture via Web Audio API, play from `AudioBuffer` for instant start. Games enable it via `build_page(..., audio_clips=True)` in their generators.

## Follow-ups (out of scope for PR 1)

- Apply console nav variant to daily / leaderboard pages.
- Per-game cover illustrations (SVG) instead of glyph gradients.
- Gamepad / TV remote D-pad navigation across spotlight + shelf.
