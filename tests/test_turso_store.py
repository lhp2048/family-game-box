import json

import httpx
import pytest

from app.storage import StorageError, health, load_json, save_json
from app.turso_store import TursoStore, pipeline_url


def test_pipeline_url_accepts_libsql_scheme():
    assert pipeline_url("libsql://box-org.turso.io") == "https://box-org.turso.io/v2/pipeline"


def test_mock_turso_roundtrip(monkeypatch):
    rows = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer token"
        body = json.loads(request.content.decode())
        results = []
        for item in body["requests"]:
            if item["type"] == "close":
                results.append({"type": "ok", "response": {"type": "close"}})
                continue
            sql = item["stmt"]["sql"]
            args = [a["value"] for a in item["stmt"].get("args") or []]
            if sql.startswith("SELECT body"):
                value = rows.get(args[0])
                row = [[{"type": "text", "value": value}]] if value is not None else []
                results.append({"type": "ok", "response": {"type": "execute", "result": {"rows": row}}})
            elif sql.startswith("INSERT"):
                rows[args[0]] = args[1]
                results.append({"type": "ok", "response": {"type": "execute", "result": {"rows": []}}})
            elif sql.startswith("SELECT 1") or sql.startswith("CREATE"):
                results.append({"type": "ok", "response": {"type": "execute", "result": {"rows": []}}})
            else:
                results.append({"type": "error", "error": {"message": sql}})
        return httpx.Response(200, json={"results": results})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = TursoStore("libsql://box-org.turso.io", "token", client=client)
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://box-org.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")
    monkeypatch.setattr("app.storage._turso_store", lambda: store)

    save_json("scores.json", {"version": 1, "entries": [{"id": "a"}]})
    assert load_json("scores.json", {})["entries"][0]["id"] == "a"
    assert health() == {"storage": "turso", "ready": True}
    client.close()


def test_turso_non_json_response_raises(monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    store = TursoStore("https://box.turso.io", "token", client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setenv("TURSO_DATABASE_URL", "https://box.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")
    monkeypatch.setattr("app.storage._turso_store", lambda: store)
    with pytest.raises(StorageError, match="暂时存不上"):
        load_json("scores.json", {"version": 1})


def test_turso_store_reused_for_same_env(monkeypatch):
    import app.storage as storage_module

    storage_module._cached_turso_store = None
    storage_module._cached_turso_key = None
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://cache-test.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "cache-token")
    first = storage_module._turso_store()
    second = storage_module._turso_store()
    assert first is second


def test_turso_store_replaced_closes_previous(monkeypatch):
    import app.storage as storage_module

    storage_module._cached_turso_store = None
    storage_module._cached_turso_key = None
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://one.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "t1")
    first = storage_module._turso_store()
    closed = {"n": 0}
    orig_close = first._client.close

    def tracking_close():
        closed["n"] += 1
        orig_close()

    first._client.close = tracking_close
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://two.turso.io")
    second = storage_module._turso_store()
    assert first is not second
    assert closed["n"] == 1


def test_turso_http_error_raises(monkeypatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down")

    store = TursoStore("https://box.turso.io", "token", client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setenv("TURSO_DATABASE_URL", "https://box.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")
    monkeypatch.setattr("app.storage._turso_store", lambda: store)
    with pytest.raises(StorageError):
        load_json("scores.json", {"version": 1})
