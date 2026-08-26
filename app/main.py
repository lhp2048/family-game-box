from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.games_catalog import list_games
from app.rank_config import rank_meta
from app.scores import get_global_leaderboard, get_leaderboard, get_personal_bests, get_recent_leaderboard, submit_score
from app.terminals import get_me, register_terminal, validate_terminal_id

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
MANIFEST_PATH = ROOT / "family-product.json"


def _load_version() -> str:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return str(data.get("version") or "0.0.0")
    except OSError:
        return "0.0.0"


app = FastAPI(title="家庭游戏盒", version=_load_version())


class RegisterBody(BaseModel):
    terminalId: str
    nickname: str = Field(min_length=1, max_length=16)


class ScoreBody(BaseModel):
    gameId: str
    mode: str
    tier: str = "default"
    tierLabel: str = ""
    display: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)


def _require_terminal_id(terminal_id: Optional[str]) -> str:
    tid = (terminal_id or "").strip()
    if not validate_terminal_id(tid):
        raise HTTPException(status_code=400, detail="missing or invalid X-Terminal-Id")
    return tid


@app.get("/api/v1/health")
async def health():
    return {
        "status": "running",
        "service": "family_game_box",
        "version": _load_version(),
        "port": 18029,
    }


@app.get("/api/v1/games")
async def games():
    return {"games": list_games()}


@app.get("/api/v1/rank/meta")
async def rank_meta_api():
    return rank_meta()


@app.get("/api/v1/terminals/me")
async def terminals_me(x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id")):
    tid = (x_terminal_id or "").strip()
    if not tid:
        return {"registered": False, "terminalId": ""}
    return get_me(tid)


@app.post("/api/v1/terminals/register")
async def terminals_register(body: RegisterBody):
    try:
        return register_terminal(body.terminalId, body.nickname)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/scores")
async def scores_submit(
    body: ScoreBody,
    x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id"),
):
    tid = _require_terminal_id(x_terminal_id)
    try:
        return submit_score(
            tid,
            body.gameId,
            body.mode,
            body.tier,
            body.metrics,
            display=body.display,
            tier_label_override=body.tierLabel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/scores/me/bests")
async def scores_my_bests(
    gameId: Optional[str] = None,
    x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id"),
):
    tid = _require_terminal_id(x_terminal_id)
    try:
        return get_personal_bests(tid, game_id=gameId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/leaderboard/recent")
async def leaderboard_recent(limit: int = 20):
    return get_recent_leaderboard(limit=min(max(limit, 1), 50))


@app.get("/api/v1/leaderboard/global")
async def leaderboard_global(limit: int = 50):
    return get_global_leaderboard(limit=min(max(limit, 1), 100))


@app.get("/api/v1/leaderboard")
async def leaderboard(gameId: str, mode: str, tier: str, limit: int = 20):
    try:
        return get_leaderboard(gameId, mode, tier, limit=min(max(limit, 1), 50))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
async def lobby():
    index = WEB_DIR / "index.html"
    if index.is_file():
        return FileResponse(index, media_type="text/html; charset=utf-8")
    return JSONResponse({"service": "family_game_box", "hint": "web/index.html missing"}, status_code=503)


@app.get("/leaderboard")
async def leaderboard_page():
    page = WEB_DIR / "leaderboard.html"
    if page.is_file():
        return FileResponse(page, media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=404, detail="leaderboard.html missing")


if (WEB_DIR / "js").is_dir():
    app.mount("/js", StaticFiles(directory=str(WEB_DIR / "js")), name="js")

if (WEB_DIR / "games").is_dir():
    app.mount("/games", StaticFiles(directory=str(WEB_DIR / "games"), html=True), name="games")
