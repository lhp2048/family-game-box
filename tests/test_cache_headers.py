from __future__ import annotations

from pathlib import Path

from app.cache_headers import CACHE_HTML, CACHE_LONG, cache_control_for_path
from tests.test_api import client, login_as, p


def test_cache_control_policy_paths():
    assert cache_control_for_path("/css/fgb-theme.css") == CACHE_LONG
    assert cache_control_for_path("/js/fgb-ui.js") == CACHE_LONG
    assert cache_control_for_path("/games/maze/index.html") == CACHE_HTML
    assert cache_control_for_path("/games/stroop/audio/red.mp3") == CACHE_LONG
    assert cache_control_for_path("/api/v1/health") is not None
    assert "no-store" in cache_control_for_path("/api/v1/health")


def test_static_css_response_has_long_cache():
    login_as(client, "cache_hdr")
    r = client.get(p("/css/fgb-theme.css"))
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "max-age=31536000" in cc
    assert "immutable" in cc


def test_game_html_has_no_cache():
    login_as(client, "cache_hdr_html")
    r = client.get(p("/games/cancel/"))
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "no-cache" in cc


def test_vercel_json_declares_asset_headers():
    root = Path(__file__).resolve().parents[1]
    import json
    import re

    config = json.loads((root / "vercel.json").read_text(encoding="utf-8"))
    headers = config.get("headers") or []
    sources = [h["source"] for h in headers]
    assert "/css/:path*" in sources
    assert "/js/:path*" in sources
    assert "/games/:path*.css" in sources
    assert "/:path*.html" in sources
    # Vercel path-to-regexp: no alternation groups like (a|b)
    for src in sources:
        assert "|" not in src, src
        assert not re.search(r"\([^)]*\|", src), src
