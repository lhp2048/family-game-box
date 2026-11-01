"""数字华容道：合法滑动洗牌始终可解。"""

from __future__ import annotations

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def solved_state(n: int) -> list[int]:
    return list(range(1, n * n)) + [0]


def shuffle_board(n: int, steps: int, seed: int) -> list[int]:
    t = (seed & 0xffffffff) or 1

    def rnd() -> float:
        nonlocal t
        t = (t + 0x6D2B79F5) & 0xFFFFFFFF
        r = ((t ^ (t >> 15)) * (1 | t)) & 0xFFFFFFFF
        r ^= (r + ((r ^ (r >> 7)) * (61 | r))) & 0xFFFFFFFF
        return ((r ^ (r >> 14)) & 0xFFFFFFFF) / 4294967296.0

    b = solved_state(n)
    blank = n * n - 1
    last_dir = -1
    for _ in range(steps):
        r, c = divmod(blank, n)
        options: list[int] = []
        for d, (dr, dc) in enumerate(DIRS):
            if last_dir >= 0 and d == (last_dir ^ 1):
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n:
                options.append(d)
        if not options:
            for d, (dr, dc) in enumerate(DIRS):
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n:
                    options.append(d)
        pick = options[int(rnd() * len(options))]
        dr, dc = DIRS[pick]
        swap = (r + dr) * n + (c + dc)
        b[blank], b[swap] = b[swap], b[blank]
        blank = swap
        last_dir = pick
    return b


def test_shuffle_is_solvable_for_all_tiers():
    tiers = [
        (4, 40, 80),
        (5, 80, 140),
        (6, 120, 220),
    ]
    for n, lo, hi in tiers:
        for seed in (1, 42, 99991):
            steps = lo + (seed % (hi - lo + 1))
            board = shuffle_board(n, steps, seed)
            assert board != solved_state(n)
            assert sorted(board) == list(range(n * n))
