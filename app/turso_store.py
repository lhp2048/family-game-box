from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from app.storage import StorageError


def pipeline_url(database_url: str) -> str:
    url = database_url.strip()
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://") :]
    url = url.rstrip("/")
    if not url.endswith("/v2/pipeline"):
        url += "/v2/pipeline"
    return url


class TursoStore:
    def __init__(self, database_url: str, auth_token: str, client: Optional[httpx.Client] = None) -> None:
        self._url = pipeline_url(database_url)
        self._token = auth_token
        self._client = client or httpx.Client(timeout=10.0)
        self._ready = False

    def ping(self) -> None:
        self._execute("SELECT 1")

    def load(self, name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure()
        rows = self._execute("SELECT body FROM documents WHERE name = ?", [name])
        if not rows:
            return dict(default)
        raw = rows[0][0]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StorageError("暂时存不上") from exc
        if not isinstance(data, dict):
            raise StorageError("暂时存不上")
        return data

    def save(self, name: str, data: Dict[str, Any]) -> None:
        self._ensure()
        body = json.dumps(data, ensure_ascii=False, indent=2)
        self._execute(
            "INSERT INTO documents (name, body) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET body = excluded.body",
            [name, body],
        )

    def _ensure(self) -> None:
        if self._ready:
            return
        self._execute(
            "CREATE TABLE IF NOT EXISTS documents ("
            "name TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        self._ready = True

    def _execute(self, sql: str, args: Optional[List[str]] = None) -> List[List[str]]:
        stmt: Dict[str, Any] = {"sql": sql}
        if args is not None:
            stmt["args"] = [{"type": "text", "value": item} for item in args]
        payload = {"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]}
        try:
            response = self._client.post(
                self._url,
                headers={"authorization": "Bearer " + self._token},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise StorageError("暂时存不上") from exc
        if response.status_code != 200:
            raise StorageError("暂时存不上")
        try:
            parsed = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise StorageError("暂时存不上") from exc
        results = parsed.get("results") or []
        if not results or results[0].get("type") != "ok":
            raise StorageError("暂时存不上")
        result = ((results[0].get("response") or {}).get("result") or {})
        rows = []
        for row in result.get("rows") or []:
            rows.append([str(cell.get("value") if isinstance(cell, dict) else cell) for cell in row])
        return rows
