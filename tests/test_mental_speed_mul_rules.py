"""Mirror mental-speed multiplication constraints (left-to-right eval)."""

from __future__ import annotations

import random
import re
from pathlib import Path

MUL_WHITELIST = {
    (4, 25),
    (8, 25),
    (5, 20),
    (2, 50),
    (4, 50),
    (5, 25),
}


def _pair(a: int, b: int) -> tuple[int, int]:
    return (min(a, b), max(a, b))


def is_mul_whitelisted(a: int, b: int) -> bool:
    return _pair(a, b) in MUL_WHITELIST


def apply_op(a: int, b: int, op: str) -> int | None:
    if op == "+":
        return a + b
    if op == "-":
        if a < b:
            return None
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0 or a % b != 0:
            return None
        return a // b
    return None


def passes_mul_rules(nums: list[int], ops: list[str]) -> bool:
    v = nums[0]
    for i, op in enumerate(ops):
        b = nums[i + 1]
        if op != "*":
            v = apply_op(v, b, op)
            if v is None:
                return False
            continue
        prod = v * b
        if prod > 100:
            if not is_mul_whitelisted(v, b):
                return False
            if i + 1 < len(ops) and ops[i + 1] == "*":
                return False
            v = prod
            continue
        v = prod
    return True


def passes_non_negative(nums: list[int], ops: list[str]) -> bool:
    v = nums[0]
    if v < 0:
        return False
    for i, op in enumerate(ops):
        v = apply_op(v, nums[i + 1], op)
        if v is None or v < 0:
            return False
    return True


def eval_left(nums: list[int], ops: list[str]) -> int | None:
    v = nums[0]
    for i, op in enumerate(ops):
        v = apply_op(v, nums[i + 1], op)
        if v is None:
            return None
    return v


def _extract_mul_whitelist_from_html() -> set[tuple[int, int]]:
    html = (Path(__file__).resolve().parents[1] / "web/games/mental-speed/index.html").read_text(
        encoding="utf-8"
    )
    keys = re.findall(r'"(\d+,\d+)"\s*:\s*true', html)
    assert keys, "MUL_WHITELIST block missing from play page"
    pairs: set[tuple[int, int]] = set()
    for key in keys:
        a, b = key.split(",")
        pairs.add(_pair(int(a), int(b)))
    return pairs


def test_whitelist_synced_with_page():
    assert _extract_mul_whitelist_from_html() == MUL_WHITELIST


def test_rejects_hard_consecutive_mul():
    assert passes_mul_rules([6, 5, 4], ["*", "*"]) is False
    assert passes_mul_rules([7, 6, 3], ["*", "*"]) is False
    assert passes_mul_rules([4, 25, 2], ["*", "*"]) is False


def test_rejects_negative_subtraction():
    assert apply_op(3, 5, "-") is None
    assert passes_non_negative([8, 3, 2], ["-", "-"]) is True
    assert passes_non_negative([2, 5, 1], ["-", "+"]) is False


def test_allows_whitelist_big_mul_only():
    assert passes_mul_rules([8, 25], ["*"])
    assert passes_mul_rules([25, 4], ["*"])
    assert passes_mul_rules([5, 20], ["*"])
    assert not passes_mul_rules([7, 15], ["*"])


def test_page_declares_min_three_operators():
    html = (Path(__file__).resolve().parents[1] / "web/games/mental-speed/index.html").read_text(
        encoding="utf-8"
    )
    assert "operatorCountForQuestion" in html
    assert "passesNonNegative" in html
    assert "operandCountForQuestion" not in html


def test_monte_carlo_generated_batch():
    """Simulate generator constraints on random expressions."""
    random.seed(42)
    violations = 0
    for _ in range(2000):
        op_count = random.choice([3, 4])
        n = op_count + 1
        nums = [random.randint(1, 12) for _ in range(n)]
        ops = [random.choice(["+", "-", "*", "/"]) for _ in range(op_count)]
        if not passes_mul_rules(nums, ops) or not passes_non_negative(nums, ops):
            continue
        ans = eval_left(nums, ops)
        if ans is None or ans < 0 or ans > 999:
            continue
        v = nums[0]
        for i, op in enumerate(ops):
            if op == "*":
                prod = v * nums[i + 1]
                if prod > 100 and not is_mul_whitelisted(v, nums[i + 1]):
                    violations += 1
                if i + 1 < len(ops) and ops[i + 1] == "*" and prod > 100:
                    violations += 1
            v = apply_op(v, nums[i + 1], op)
            if v is None:
                break
    assert violations == 0
