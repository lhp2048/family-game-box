#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""穷举整数四则运算下的 24 点全部解法。"""

from __future__ import annotations

import argparse
import itertools
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

OPS = ("+", "-", "*", "/")
TARGET = 24


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
    raise ValueError("unknown op: %r" % (op,))


@lru_cache(maxsize=None)
def _ways(nums: Tuple[int, ...]) -> frozenset:
    """用尽 nums 中每个数恰好一次，得到所有 (值, 表达式)。"""
    nums = tuple(sorted(nums))
    if len(nums) == 1:
        v = nums[0]
        return frozenset(((v, str(v)),))

    items = list(nums)
    n = len(items)
    out: Set[Tuple[int, str]] = set()

    # 分治：划成两个非空子集，分别求值后再四则合并
    for mask in range(1, (1 << n) - 1):
        left: List[int] = []
        right: List[int] = []
        for idx in range(n):
            if mask & (1 << idx):
                left.append(items[idx])
            else:
                right.append(items[idx])
        left_t = tuple(sorted(left))
        right_t = tuple(sorted(right))
        # 子集无序：只保留 left <= right，避免同一划分算两次
        if left_t > right_t:
            continue
        for lv, le in _ways(left_t):
            for rv, re in _ways(right_t):
                for op in OPS:
                    for x, y, ex, ey in ((lv, rv, le, re), (rv, lv, re, le)):
                        if op in ("+", "*") and (ex, x) > (ey, y):
                            continue
                        r = apply_op(x, y, op)
                        if r is None:
                            continue
                        out.add((r, "(%s%s%s)" % (ex, op, ey)))
    return frozenset(out)


def solve_combo(nums: Tuple[int, ...]) -> Set[str]:
    found: Set[str] = set()
    for value, expr in _ways(tuple(sorted(nums))):
        if value == TARGET:
            found.add(expr)
    return found


def enumerate_all(min_n: int, max_n: int) -> Dict:
    combos = list(
        itertools.combinations_with_replacement(range(min_n, max_n + 1), 4)
    )
    solutions: Dict[Tuple[int, ...], List[str]] = {}
    solvable = 0
    total = len(combos)
    for idx, combo in enumerate(combos, 1):
        exprs = solve_combo(combo)
        if exprs:
            solutions[combo] = sorted(exprs)
            solvable += 1
        if idx % 2000 == 0 or idx == total:
            print(
                "  progress %d/%d (solvable=%d, cache=%d)"
                % (idx, total, solvable, _ways.cache_info().currsize),
                flush=True,
            )
    return {
        "total": total,
        "solvable": solvable,
        "unsolvable": total - solvable,
        "expr_count": sum(len(v) for v in solutions.values()),
        "solutions": solutions,
    }


def write_outputs(
    out_dir: Path,
    result: Dict,
    elapsed: float,
    min_n: int,
    max_n: int,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "summary.txt"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("24 Points Enumeration (integer arithmetic)\n")
        f.write("=" * 48 + "\n")
        f.write("Range: %d .. %d (inclusive)\n" % (min_n, max_n))
        f.write("Rules: + - * / ; division only when exact; no divide by zero\n")
        f.write("Target: %d\n" % TARGET)
        f.write("Duplicates allowed; combos normalized ascending\n")
        f.write("\n")
        f.write("Total combos:      %d\n" % result["total"])
        f.write("Solvable combos:   %d\n" % result["solvable"])
        f.write("Unsolvable combos: %d\n" % result["unsolvable"])
        f.write("Total expressions: %d\n" % result["expr_count"])
        f.write("Elapsed seconds:   %.3f\n" % elapsed)

    solutions_path = out_dir / "solutions.txt"
    with solutions_path.open("w", encoding="utf-8") as f:
        for combo, exprs in sorted(result["solutions"].items()):
            nums = ", ".join(str(x) for x in combo)
            f.write("[%s]  (%d solutions)\n" % (nums, len(exprs)))
            for expr in exprs:
                f.write("  %s\n" % expr)
            f.write("\n")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enumerate integer 24-point solutions for 4-number combos."
    )
    parser.add_argument("--min", type=int, default=0, dest="min_n", help="min number")
    parser.add_argument("--max", type=int, default=24, dest="max_n", help="max number")
    parser.add_argument(
        "--out", type=str, default="output", help="output directory"
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    if args.min_n > args.max_n:
        raise SystemExit("--min must be <= --max")

    _ways.cache_clear()
    started = time.perf_counter()
    result = enumerate_all(args.min_n, args.max_n)
    elapsed = time.perf_counter() - started
    write_outputs(Path(args.out), result, elapsed, args.min_n, args.max_n)

    print("Done.")
    print("  combos:      %d" % result["total"])
    print("  solvable:    %d" % result["solvable"])
    print("  unsolvable:  %d" % result["unsolvable"])
    print("  expressions: %d" % result["expr_count"])
    print("  elapsed:     %.3fs" % elapsed)
    print("  wrote:       %s" % Path(args.out).resolve())


if __name__ == "__main__":
    main()
