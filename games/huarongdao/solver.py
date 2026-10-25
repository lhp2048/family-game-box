#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Macro-move BFS/Dijkstra for 华容道 (same-piece slides = 0 extra cost; switch piece = +1)."""

from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROWS, COLS = 5, 4
ESCAPE_ROW, ESCAPE_COL = 3, 1  # Cao 2×2 top-left at win


@dataclass(frozen=True)
class Block:
    w: int  # cols
    h: int  # rows
    r: int
    c: int

    @property
    def id_key(self) -> Tuple[int, int, int, int]:
        return (self.w, self.h, self.r, self.c)


def blocks_from_jeantimex(blocks_json: List[dict]) -> List[Block]:
    out: List[Block] = []
    for b in blocks_json:
        sh = b["shape"]
        h, w = int(sh[0]), int(sh[1])
        pos = b["position"]
        r, c = int(pos[0]), int(pos[1])
        out.append(Block(w=w, h=h, r=r, c=c))
    return out


def blocks_to_pieces(blocks: List[Block]) -> List[dict]:
    """Export for game JSON (Cao = index 0)."""
    pieces: List[dict] = []
    labels = {
        (2, 2): ("cao", "曹"),
        (2, 1): ("v", "将"),
        (1, 2): ("guan", "关"),
        (1, 1): ("s", "兵"),
    }
    v_n = 0
    s_n = 0
    for i, b in enumerate(blocks):
        if b.w == 2 and b.h == 2:
            kind, lab = "cao", "曹"
        elif b.w == 1 and b.h == 2:
            v_n += 1
            kind, lab = "v", ["张", "马", "关", "黄", "赵", "将"][min(v_n - 1, 5)]
        elif b.w == 2 and b.h == 1:
            kind, lab = "guan", "关"
        else:
            s_n += 1
            kind, lab = "s", "兵"
        pieces.append(
            {
                "id": "cao" if kind == "cao" else ("%s%d" % (kind, i)),
                "type": kind,
                "label": lab,
                "r": b.r,
                "c": b.c,
                "w": b.w,
                "h": b.h,
            }
        )
    return pieces


def state_key(blocks: List[Block]) -> Tuple[Tuple[int, int], ...]:
    return tuple((b.r, b.c) for b in blocks)


def build_occupancy(blocks: List[Block]) -> List[List[int]]:
    grid = [[-1] * COLS for _ in range(ROWS)]
    for i, b in enumerate(blocks):
        for dr in range(b.h):
            for dc in range(b.w):
                grid[b.r + dr][b.c + dc] = i
    return grid


def can_place(grid: List[List[int]], b: Block, r: int, c: int, skip: int) -> bool:
    if r < 0 or c < 0 or r + b.h > ROWS or c + b.w > COLS:
        return False
    for dr in range(b.h):
        for dc in range(b.w):
            cell = grid[r + dr][c + dc]
            if cell != -1 and cell != skip:
                return False
    return True


def is_win(blocks: List[Block]) -> bool:
    cao = blocks[0]
    return cao.r == ESCAPE_ROW and cao.c == ESCAPE_COL


def neighbors(
    blocks: List[Block], last_piece: int
) -> List[Tuple[Tuple[Tuple[int, int], ...], int, int]]:
    """Returns (new_key, piece_idx, macro_cost)."""
    grid = build_occupancy(blocks)
    out: List[Tuple[Tuple[Tuple[int, int], ...], int, int]] = []
    for i, b in enumerate(blocks):
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = b.r + dr, b.c + dc
            if not can_place(grid, b, nr, nc, i):
                continue
            nb = list(blocks)
            nb[i] = Block(b.w, b.h, nr, nc)
            macro = 0 if last_piece == i else 1
            out.append((state_key(nb), i, macro))
    return out


def min_macro_steps(blocks: List[Block], max_states: int = 400_000) -> Optional[int]:
    start = state_key(blocks)
    if is_win(blocks):
        return 0
    # (cost, counter, key, last_piece)
    pq: List[Tuple[int, int, Tuple[Tuple[int, int], ...], int]] = []
    heapq.heappush(pq, (0, 0, start, -1))
    best: Dict[Tuple[Tuple[Tuple[int, int], ...], int], int] = {(start, -1): 0}
    seen = 0
    while pq:
        cost, _, key, last = heapq.heappop(pq)
        if cost != best.get((key, last), cost + 1):
            continue
        seen += 1
        if seen > max_states:
            return None
        bl = _key_to_blocks(key, blocks)
        if is_win(bl):
            return cost
        for nkey, piece, mc in neighbors(bl, last):
            nc = cost + mc
            st = (nkey, piece)
            if nc < best.get(st, 1_000_000):
                best[st] = nc
                heapq.heappush(pq, (nc, seen, nkey, piece))
    return None


def _key_to_blocks(key: Tuple[Tuple[int, int], ...], template: List[Block]) -> List[Block]:
    out: List[Block] = []
    for i, (r, c) in enumerate(key):
        t = template[i]
        out.append(Block(t.w, t.h, r, c))
    return out


def rebuild_blocks(key: Tuple[Tuple[int, int], ...], template: List[Block]) -> List[Block]:
    return _key_to_blocks(key, template)


def optimal_path(blocks: List[Block], max_states: int = 500_000) -> Optional[List[Tuple[Tuple[int, int], ...]]]:
    """Return list of state keys from start to win (inclusive), macro-optimal."""
    start = state_key(blocks)
    template = blocks
    if is_win(blocks):
        return [start]
    pq: List[Tuple[int, int, Tuple[Tuple[int, int], ...], int]] = []
    heapq.heappush(pq, (0, 0, start, -1))
    best: Dict[Tuple[Tuple[Tuple[int, int], ...], int], int] = {(start, -1): 0}
    parent: Dict[Tuple[Tuple[Tuple[int, int], ...], int], Tuple[Tuple[Tuple[int, int], ...], int]] = {}
    seen = 0
    win_state: Optional[Tuple[Tuple[int, int], ...]] = None
    win_last = -1
    while pq:
        cost, _, key, last = heapq.heappop(pq)
        st = (key, last)
        if cost != best.get(st, cost + 1):
            continue
        seen += 1
        if seen > max_states:
            return None
        bl = _key_to_blocks(key, template)
        if is_win(bl):
            win_state = key
            win_last = last
            break
        for nkey, piece, mc in neighbors(bl, last):
            nc = cost + mc
            nst = (nkey, piece)
            if nc < best.get(nst, 1_000_000):
                best[nst] = nc
                parent[nst] = st
                heapq.heappush(pq, (nc, seen, nkey, piece))
    if win_state is None:
        return None
    # walk back
    path_keys = [win_state]
    cur = (win_state, win_last)
    while cur in parent:
        cur = parent[cur]
        path_keys.append(cur[0])
    path_keys.reverse()
    return path_keys


def state_at_macro_distance_from_win(
    blocks: List[Block], macro_steps_from_win: int
) -> Optional[List[Block]]:
    """Walk backward along one macro-optimal path from win."""
    path = optimal_path(blocks)
    if not path:
        return None
    idx = max(0, len(path) - 1 - macro_steps_from_win)
    return _key_to_blocks(path[idx], blocks)


def load_jeantimex(path: Path) -> List[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    data = load_jeantimex(Path(__file__).parent / "hrd-games.json")
    for g in data:
        if g["name"] == "横刀立马":
            bl = blocks_from_jeantimex(g["blocks"])
            print("macro min", min_macro_steps(bl))
            break
