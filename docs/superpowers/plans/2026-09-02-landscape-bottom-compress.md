# 横屏压扁对局底栏 Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 横屏/矮视口时压扁对局底栏，让棋盘更大。

**Architecture:** 仅 CSS（数独加一层 `play-chrome` 包装以便横屏 `display: contents` 合成一行）。改 generate 源后跑 games build。

**Tech Stack:** HTML/CSS，Python generate 脚本

## Global Constraints

- 触发 media query 与现网一致
- 竖屏布局与文案不变
- 不改玩法 / API

---

### Task 1: game_common 共用 `.actions` 压矮

**Files:** `games/common/game_common.py`

- [x] 在现有矮视口 query 内把 `.actions` / 按钮 padding 再压一档

### Task 2: 数独底栏横屏合成一行

**Files:** `games/sudoku/generate.py`

- [x] BODY：用 `.play-chrome` 包住 `tool-row` + `play-actions`
- [x] CSS：竖屏仍上下叠；横屏 `play-chrome` 7 列 + `display: contents`，并压矮 numpad

### Task 3: 24 点底栏压矮 + 构建

**Files:** `games/24points/generate_play.py`；`games/schulte/index.html`

- [x] 矮视口 query 内压 `.ops` / `.actions`
- [x] 跑 generate / build_page 更新 `web/games/**`
