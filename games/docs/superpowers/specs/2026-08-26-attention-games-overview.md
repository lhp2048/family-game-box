# 专注力训练游戏 · 总览

**日期:** 2026-08-26  
**状态:** 实现中（生成器与静态页已就绪）

## 目标

在现有 `games` 工程（Python 生成器 + 静态 HTML）上，扩展一组**认知专注力训练**小游戏。风格、模式选择与结算页与 `quiz.html`（24 点出题页）保持一致。

## 游戏清单

| 游戏 | 文档 | 静态页 | 生成器 | 感官 | 核心训练 |
|------|------|--------|--------|------|----------|
| 数独 | [sudoku-design](./2026-08-26-sudoku-design.md) | `sudoku.html` | `generate_sudoku.py` | 视觉 + 逻辑 | 逻辑推理、持续专注 |
| Stroop 色字干扰 | [stroop-design](./2026-08-26-stroop-design.md) | `stroop.html` | `generate_stroop.py` | 视觉 | 抗干扰、选择性注意 |
| 数字/汉字划销 | [cancel-design](./2026-08-26-cancel-design.md) | `cancel.html` | `generate_cancel.py` | 视觉 | 视觉搜索、细节捕捉 |
| 迷宫 | [maze-design](./2026-08-26-maze-design.md) | `maze.html` | `generate_maze.py` | 视觉 + 运动 | 路径预判、视觉追踪 |
| 找不同 | [spot-diff-design](./2026-08-26-spot-diff-design.md) | `spot_diff.html` | `generate_spot_diff.py` | 视觉 | 细致观察、系统扫描 |
| Simon Says（老师说） | [simon-design](./2026-08-26-simon-design.md) | `simon.html` | `generate_simon.py` | 听觉 + 运动 | 听觉专注、冲动控制 |

## 通用模式（各游戏统一）

| 模式 | 行为 |
|------|------|
| 休闲 | 随机出题/关卡；可下一题；不计时；无强制结算 |
| 挑战 | 开局选题量或时长；计时；结束后统计正确率、用时、连击等 |
| 退出 | 回模式选择（挑战中可二次确认） |
| 重来 | 重置当前关或当前轮 |

## 通用 UI

- 复用 `generate_quiz.py` 的 CSS 变量（`--ink`、`--paper`、`--accent` 等）、卡片布局、模式选择网格、结算面板。
- 移动端优先：`viewport`、触控友好按钮、最小点击区域 44px。
- 语言：`lang="zh-CN"`，界面中文；Stroop / Simon 可预留英文动作库扩展位。

## 目录与构建（规划）

```
games/
  generate_sudoku.py
  generate_stroop.py
  generate_cancel.py
  generate_maze.py
  generate_spot_diff.py
  generate_simon.py
  output/
    sudoku.html  stroop.html  cancel.html
    maze.html    spot_diff.html  simon.html
  dist/          # 同上，发布副本
  scripts/
    build.bat    # 扩展：一并构建全部页面
```

## 建议实现顺序

1. **Stroop**、**划销** — 生成与交互最简单，可快速验证通用模式框架。
2. **Simon Says** — 规则清晰，冲动控制指标有训练价值。
3. **找不同（符号矩阵版）** — 与划销共享网格组件。
4. **迷宫** — 需迷宫算法与拖动/步进交互。
5. **数独** — 唯一解校验与候选数 UI 工作量最大。

## 非目标（系列共性）

- 不做账号、云端同步、排行榜后端。
- 不做原生 App（首期仅静态 HTML；后续可复用逻辑移植 Flutter / 原生）。
- 插画素材版找不同、预录制 TTS 音频包列为二期可选。

## 成功标准（系列）

- 每款游戏可独立打开对应 HTML，离线可用。
- 休闲与挑战模式均可完整走通一局并显示结算。
- `scripts/build.bat` 一键产出 `dist/` 下全部页面（实现阶段验收）。
