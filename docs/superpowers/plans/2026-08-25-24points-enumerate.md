# 24 点穷举 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Python 穷举 0~24 有放回四元组在整数四则运算下得到 24 的全部解法，并写入 `output/summary.txt` 与 `output/solutions.txt`。

**Architecture:** 单文件 `solve_24.py`：升序枚举四元组 → 排列去重 → 递归二分合并（整除约束）→ 表达式去重 → 写文件。

**Tech Stack:** Python 3 标准库（`argparse`、`itertools`、`pathlib`、`time`）

## Global Constraints

- 数字范围默认 `0..24`（含），有放回，升序归一
- `/` 仅当 `b != 0` 且 `a % b == 0`
- 仅标准库；输出目录默认 `output/`
- 无解组合不写入 `solutions.txt`

---

### Task 1: 求解核心 `solve_combo`

**Files:**
- Create: `solve_24.py`
- Test: 手动/`python -c` 验证经典组

**Interfaces:**
- Produces: `solve_combo(nums: tuple[int, ...]) -> set[str]`
- Produces: `apply_op(a: int, b: int, op: str) -> int | None`

- [ ] **Step 1: 实现 `apply_op` 与递归求解**

```python
from __future__ import annotations

import itertools
from typing import Iterable, List, Optional, Set, Tuple


OPS = ("+", "-", "*", "/")


def apply_op(a: int, b: int, op: str) -> Optional[int]:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0 or a % b != 0:
            return None
        return a // b
    raise ValueError(op)


def _search(values: List[int], exprs: List[str], found: Set[str]) -> None:
    if len(values) == 1:
        if values[0] == 24:
            found.add(exprs[0])
        return
    n = len(values)
    for i, j in itertools.combinations(range(n), 2):
        a, b = values[i], values[j]
        ea, eb = exprs[i], exprs[j]
        rest_v = [values[k] for k in range(n) if k != i and k != j]
        rest_e = [exprs[k] for k in range(n) if k != i and k != j]
        for op in OPS:
            for x, y, ex, ey in ((a, b, ea, eb), (b, a, eb, ea)):
                if op in ("+", "*") and (x, ex) > (y, ey):
                    continue  # 交换律去重一侧
                r = apply_op(x, y, op)
                if r is None:
                    continue
                _search(rest_v + [r], rest_e + [f"({ex}{op}{ey})"], found)


def solve_combo(nums: Tuple[int, ...]) -> Set[str]:
    found: Set[str] = set()
    for perm in set(itertools.permutations(nums)):
        _search(list(perm), [str(x) for x in perm], found)
    return found
```

- [ ] **Step 2: 验证 `3,3,8,8` 有解（整数路径，例如 `(3*8)*(8/8)`）**

Run: `python -c "from solve_24 import solve_combo; print(sorted(solve_combo((3,3,8,8))))"`

Expected: 非空集合，且每条表达式在整除规则下可求值到 24

---

### Task 2: 穷举与写文件 + CLI

**Files:**
- Modify: `solve_24.py`
- Create: `output/summary.txt`, `output/solutions.txt`（运行时生成）

**Interfaces:**
- Consumes: `solve_combo`
- Produces: `enumerate_all(min_n: int, max_n: int) -> dict`
- Produces: `write_outputs(out_dir, result, elapsed, min_n, max_n)`
- Produces: `main()`

- [ ] **Step 1: 实现枚举、写文件、argparse**

```python
def enumerate_all(min_n: int, max_n: int):
    combos = list(itertools.combinations_with_replacement(range(min_n, max_n + 1), 4))
    solutions = {}
    solvable = 0
    for combo in combos:
        exprs = solve_combo(combo)
        if exprs:
            solutions[combo] = sorted(exprs)
            solvable += 1
    return {
        "total": len(combos),
        "solvable": solvable,
        "unsolvable": len(combos) - solvable,
        "expr_count": sum(len(v) for v in solutions.values()),
        "solutions": solutions,
    }


def write_outputs(out_dir, result, elapsed, min_n, max_n):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = out / "summary.txt"
    solutions = out / "solutions.txt"
    # write summary stats + solutions groups as per spec
```

- [ ] **Step 2: 全量运行**

Run: `python solve_24.py --min 0 --max 24 --out output`

Expected: 生成 `output/summary.txt`、`output/solutions.txt`；summary 中有组合数与耗时

- [ ] **Step 3: 抽查 summary 数字与 solutions 格式**

Run: 读 `summary.txt` 头几行；在 `solutions.txt` 中确认存在 `[3, 3, 8, 8]` 块

---

## Spec coverage

| Spec | Task |
|------|------|
| 0~24 有放回升序 | Task 2 |
| 整数整除规则 | Task 1 |
| 递归二分合并 | Task 1 |
| summary + solutions | Task 2 |
| CLI `--min/--max/--out` | Task 2 |
