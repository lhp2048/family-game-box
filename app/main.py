from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.datastructures import MutableHeaders

from app import daily_admin as daily_admin_mod
from app import daily_challenges as daily_challenges_mod
from app import daily_runs as daily_runs_mod
from app import difficulty as difficulty_mod
from app import lobby as lobby_mod
from app.games_catalog import list_games
from app.html_prefix import read_response_body, rewrite_html
from app.rank_config import rank_meta
from app.root_path import get_root_path
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


def _health_payload() -> Dict[str, Any]:
    return {
        "status": "running",
        "service": "family_game_box",
        "version": _load_version(),
        "port": 18029,
        "rootPath": get_root_path() or "/",
    }


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


class PasswordBody(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class TemplateBody(BaseModel):
    stages: list = Field(default_factory=list)


class DailyRunPatchBody(BaseModel):
    action: str
    stageIndex: int = 0
    timeMs: int = 0
    totalTimeMs: int = 0
    stage: Optional[Dict[str, Any]] = None


class DifficultyPutBody(BaseModel):
    games: Dict[str, Any] = Field(default_factory=dict)


class DifficultyResetBody(BaseModel):
    gameId: str = ""


def create_app() -> FastAPI:
    prefix = get_root_path()
    app = FastAPI(title="家庭游戏盒", version=_load_version())
    router = APIRouter()
    _register_routes(router)
    app.include_router(router, prefix=prefix)

    _mount_static(app, prefix)

    if prefix:
        @app.get("/api/v1/health")
        async def health_alias():
            """Unprefixed health for installers / portal discovery."""
            return _health_payload()

        @app.get("/")
        async def root_redirect():
            return RedirectResponse(url=prefix + "/", status_code=307)

        @app.middleware("http")
        async def html_prefix_middleware(request: Request, call_next):
            response = await call_next(request)
            ctype = response.headers.get("content-type", "")
            if "text/html" not in ctype:
                return response
            body = await read_response_body(response)
            text = rewrite_html(body.decode("utf-8", errors="replace"), prefix)
            data = text.encode("utf-8")
            headers = MutableHeaders(response.headers)
            headers["content-length"] = str(len(data))
            return Response(
                content=data,
                status_code=response.status_code,
                headers=dict(headers),
                media_type="text/html; charset=utf-8",
            )

    return app


def _mount_static(app: FastAPI, prefix: str) -> None:
    def mount_at(sub: str, directory: Path, html: bool = False) -> None:
        if not directory.is_dir():
            return
        path = (prefix + sub) if prefix else sub
        app.mount(path, StaticFiles(directory=str(directory), html=html), name=sub.strip("/"))

    mount_at("/js", WEB_DIR / "js")
    mount_at("/css", WEB_DIR / "css")
    mount_at("/games", WEB_DIR / "games", html=True)


def _register_routes(api: APIRouter) -> None:
    def _require_terminal_id(terminal_id: Optional[str]) -> str:
        tid = (terminal_id or "").strip()
        if not validate_terminal_id(tid):
            raise HTTPException(status_code=400, detail="missing or invalid X-Terminal-Id")
        return tid

    def _map_exc(exc: Exception) -> HTTPException:
        if isinstance(exc, PermissionError):
            return HTTPException(status_code=401, detail=str(exc))
        if isinstance(exc, ValueError):
            return HTTPException(status_code=400, detail=str(exc))
        return HTTPException(status_code=500, detail="internal error")

    @api.get("/api/v1/health")
    async def health():
        return _health_payload()

    @api.get("/api/v1/games")
    async def games():
        return {"games": list_games()}

    @api.get("/api/v1/rank/meta")
    async def rank_meta_api():
        return rank_meta()

    @api.get("/api/v1/terminals/me")
    async def terminals_me(x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id")):
        tid = (x_terminal_id or "").strip()
        if not tid:
            return {"registered": False, "terminalId": ""}
        return get_me(tid)

    @api.post("/api/v1/terminals/register")
    async def terminals_register(body: RegisterBody):
        try:
            return register_terminal(body.terminalId, body.nickname)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/v1/scores")
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

    @api.get("/api/v1/scores/me/bests")
    async def scores_my_bests(
        gameId: Optional[str] = None,
        x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id"),
    ):
        tid = _require_terminal_id(x_terminal_id)
        try:
            return get_personal_bests(tid, game_id=gameId)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/v1/leaderboard/recent")
    async def leaderboard_recent(limit: int = 20):
        return get_recent_leaderboard(limit=min(max(limit, 1), 50))

    @api.get("/api/v1/leaderboard/global")
    async def leaderboard_global(limit: int = 50):
        return get_global_leaderboard(limit=min(max(limit, 1), 100))

    @api.get("/api/v1/leaderboard")
    async def leaderboard(gameId: str, mode: str, tier: str, limit: int = 20):
        try:
            return get_leaderboard(gameId, mode, tier, limit=min(max(limit, 1), 50))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/v1/daily/today")
    async def daily_today():
        try:
            return daily_challenges_mod.ensure_today()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/v1/daily/runs")
    async def daily_runs_start(x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id")):
        tid = _require_terminal_id(x_terminal_id)
        try:
            return daily_runs_mod.start_run(tid)
        except (ValueError, PermissionError) as exc:
            raise _map_exc(exc) from exc

    @api.patch("/api/v1/daily/runs/{run_id}")
    async def daily_runs_patch(
        run_id: str,
        body: DailyRunPatchBody,
        x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id"),
    ):
        tid = _require_terminal_id(x_terminal_id)
        try:
            return daily_runs_mod.patch_run(tid, run_id, body.model_dump())
        except (ValueError, PermissionError) as exc:
            raise _map_exc(exc) from exc

    @api.get("/api/v1/daily/leaderboard")
    async def daily_leaderboard(
        date: Optional[str] = None,
        comboId: Optional[str] = None,
        limit: int = 50,
    ):
        return daily_runs_mod.leaderboard(
            date=date,
            combo_id=comboId,
            limit=min(max(limit, 1), 100),
        )

    @api.get("/api/v1/lobby/summary")
    async def lobby_summary(x_terminal_id: Optional[str] = Header(default=None, alias="X-Terminal-Id")):
        tid = (x_terminal_id or "").strip() or None
        return lobby_mod.get_lobby_summary(tid)

    @api.get("/api/v1/admin/status")
    async def admin_status(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
        return daily_admin_mod.admin_status(x_admin_token)

    @api.post("/api/v1/admin/setup")
    async def admin_setup(body: PasswordBody):
        try:
            return daily_admin_mod.setup_password(body.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/v1/admin/login")
    async def admin_login(body: PasswordBody):
        try:
            return daily_admin_mod.login(body.password)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @api.post("/api/v1/admin/logout")
    async def admin_logout(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
        daily_admin_mod.logout(x_admin_token or "")
        return {"ok": True}

    @api.get("/api/v1/admin/daily/template")
    async def admin_template_get(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
        try:
            daily_admin_mod.require_admin(x_admin_token)
            return daily_admin_mod.get_template()
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @api.put("/api/v1/admin/daily/template")
    async def admin_template_put(
        body: TemplateBody,
        x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    ):
        try:
            daily_admin_mod.require_admin(x_admin_token)
            return daily_admin_mod.put_template(body.stages)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/v1/admin/daily/regenerate")
    async def admin_regenerate(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
        try:
            daily_admin_mod.require_admin(x_admin_token)
            return daily_challenges_mod.regenerate()
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/v1/admin/daily/history")
    async def admin_history(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
        try:
            daily_admin_mod.require_admin(x_admin_token)
            return {"history": daily_challenges_mod.get_history()}
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @api.get("/api/v1/difficulty")
    async def difficulty_get(gameId: Optional[str] = None):
        try:
            return difficulty_mod.get_difficulty(gameId)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/v1/difficulty/defaults")
    async def difficulty_defaults(gameId: Optional[str] = None):
        data = difficulty_mod.default_difficulty()
        if gameId:
            if gameId not in data["games"]:
                raise HTTPException(status_code=400, detail="unknown gameId")
            return {"version": 1, "updatedAt": "", "games": {gameId: data["games"][gameId]}}
        return data

    @api.put("/api/v1/admin/difficulty")
    async def difficulty_put(
        body: DifficultyPutBody,
        x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    ):
        try:
            daily_admin_mod.require_admin(x_admin_token)
            return difficulty_mod.put_difficulty(body.games)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/v1/admin/difficulty/reset")
    async def difficulty_reset(
        body: DifficultyResetBody,
        x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    ):
        try:
            daily_admin_mod.require_admin(x_admin_token)
            gid = (body.gameId or "").strip() or None
            return difficulty_mod.reset_difficulty(gid)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/")
    async def lobby():
        index = WEB_DIR / "index.html"
        if index.is_file():
            return FileResponse(index, media_type="text/html; charset=utf-8")
        return JSONResponse({"service": "family_game_box", "hint": "web/index.html missing"}, status_code=503)

    @api.get("/leaderboard")
    async def leaderboard_page():
        page = WEB_DIR / "leaderboard.html"
        if page.is_file():
            return FileResponse(page, media_type="text/html; charset=utf-8")
        raise HTTPException(status_code=404, detail="leaderboard.html missing")

    @api.get("/daily")
    async def daily_page():
        page = WEB_DIR / "daily.html"
        if page.is_file():
            return FileResponse(page, media_type="text/html; charset=utf-8")
        raise HTTPException(status_code=404, detail="daily.html missing")

    @api.get("/daily/leaderboard")
    async def daily_leaderboard_page():
        page = WEB_DIR / "daily-leaderboard.html"
        if page.is_file():
            return FileResponse(page, media_type="text/html; charset=utf-8")
        raise HTTPException(status_code=404, detail="daily-leaderboard.html missing")

    @api.get("/admin")
    async def admin_page():
        page = WEB_DIR / "admin.html"
        if page.is_file():
            return FileResponse(page, media_type="text/html; charset=utf-8")
        raise HTTPException(status_code=404, detail="admin.html missing")


app = create_app()
