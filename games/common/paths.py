#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified web/dist/build paths for family_game_box games."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return REPO_ROOT


def game_page_paths(slug: str, filename: str = "index.html") -> tuple[Path, Path, Path]:
    """Return (build_cache, web_runtime, dist_package) for one static page."""
    module_dir = REPO_ROOT / "games" / slug.replace("-", "_")
    build = module_dir / "build" / filename
    web = REPO_ROOT / "web" / "games" / slug / filename
    dist = REPO_ROOT / "dist" / "web" / "games" / slug / filename
    return build, web, dist


def points_page_paths(filename: str) -> tuple[Path, Path, Path]:
    """24-point pages use play.html / library.html instead of index.html."""
    build = REPO_ROOT / "games" / "24points" / "build" / filename
    web = REPO_ROOT / "web" / "games" / "24points" / filename
    dist = REPO_ROOT / "dist" / "web" / "games" / "24points" / filename
    return build, web, dist
