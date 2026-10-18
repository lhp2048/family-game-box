"""Vercel Python entry. Set ROOT_PATH empty, plus TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.

Preview 使用单独的 Turso 数据库，不要填生产库的地址。
"""

from app.main import app

__all__ = ["app"]
