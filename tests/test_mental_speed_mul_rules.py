"""Mirror mental-speed rules (standard ×÷ before +− precedence)."""

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


def eval_with_precedence(nums: list[int], ops: list[str]) -> int | None:
    values = list(nums)
    operators = list(ops)
    i = 0
    while i < len(operators):
        op = operators[i]
        if op not in ("*", "/"):
            i += 1
            continue
        r = apply_op(values[i], values[i + 1], op)
        if r is None:
            return None
        values[i : i + 2] = [r]
        operators.pop(i)
    if not values:
        return None
    v = values[0]
    for j, op in enumerate(operators):
        v = apply_op(v, values[j + 1], op)
        if v is None:
            return None
    return v


def eval_left(nums: list[int], ops: list[str]) -> int | None:
    v = nums[0]
    for i, op in enumerate(ops):
        v = apply_op(v, nums[i + 1], op)
        if v is None:
            return None
    return v


def passes_mul_rules(nums: list[int], ops: list[str]) -> bool:
    values = list(nums)
    operators = list(ops)
    i = 0
    while i < len(operators):
        op = operators[i]
        if op not in ("*", "/"):
            i += 1
            continue
        a, b = values[i], values[i + 1]
        if op == "*":
            prod = a * b
            if prod > 100:
                if not is_mul_whitelisted(a, b):
                    return False
                if i + 1 < len(operators) and operators[i + 1] == "*":
                    return False
        r = apply_op(a, b, op)
        if r is None:
            return False
        values[i : i + 2] = [r]
        operators.pop(i)
    return True


def passes_non_negative(nums: list[int], ops: list[str]) -> bool:
    ans = eval_with_precedence(nums, ops)
    return ans is not None and ans >= 0


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


def test_standard_precedence_not_left_to_right():
    nums = [2, 3, 4]
    ops = ["+", "*"]
    assert eval_left(nums, ops) == 20
    assert eval_with_precedence(nums, ops) == 14


def test_standard_precedence_mixed_ops():
    assert eval_with_precedence([2, 3, 4, 1], ["+", "*", "-"]) == 13
    assert eval_with_precedence([10, 6, 2], ["-", "/"]) == 7


def test_page_uses_precedence_eval():
    html = (Path(__file__).resolve().parents[1] / "web/games/mental-speed/index.html").read_text(
        encoding="utf-8"
    )
    assert "evalWithPrecedence" in html
    assert "evalLeft" not in html
    assert "先乘除后加减" in html


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
    assert "ms-countdown" not in html


def test_monte_carlo_generated_batch():
    """Simulate generator constraints on random expressions."""
    random.seed(42)
    for _ in range(2000):
        op_count = random.choice([3, 4])
        n = op_count + 1
        nums = [random.randint(1, 12) for _ in range(n)]
        ops = [random.choice(["+", "-", "*", "/"]) for _ in range(op_count)]
        if not passes_mul_rules(nums, ops) or not passes_non_negative(nums, ops):
            continue
        ans = eval_with_precedence(nums, ops)
        assert ans is not None and 0 <= ans <= 999
