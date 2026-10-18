from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_storage_backend(monkeypatch):
    """Keep the suite on file storage unless a test opts into Turso."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    from app.storage import reset_backend_cache

    reset_backend_cache()
    yield
    reset_backend_cache()
