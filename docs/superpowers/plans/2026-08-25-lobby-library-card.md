# 大厅解法库卡片 + 返回大厅 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 大厅第三张解法库卡片；24 点 / 舒尔特 / 解法库首页统一「← 返回大厅」。

**Architecture:** 静态大厅卡 + 生成脚本注入链接；不改 games API。

**Tech Stack:** 静态 HTML/CSS/JS，`generate_play.py` / `generate_html.py`，pytest。

---

### Task 1: 大厅第三卡

**Files:** `web/index.html`, sync `dist/web/index.html`, `tests/test_api.py`

- 网格增加解法库卡；删 secondary 链；断言第三卡与 library 路径。

### Task 2: 各首页返回大厅

**Files:** `generate_play.py`, `generate_html.py`, `web/games/schulte/index.html`

- 文案 `← 返回大厅`，`href="/"`。
- 跑 generate 脚本同步 web/dist；pytest 全绿。
