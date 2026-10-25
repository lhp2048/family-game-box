"""Response security headers tuned for static games + inline scripts."""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Inline script/style required by game HTML and lobby pages.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "media-src 'self' blob:; "
    "worker-src 'self' blob:"
)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                names = {k.decode("latin-1").lower() for k, _ in headers}
                extra = [
                    (b"x-frame-options", b"DENY"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"content-security-policy", CONTENT_SECURITY_POLICY.encode("latin-1")),
                ]
                for key, val in extra:
                    if key.decode("latin-1") not in names:
                        headers.append((key, val))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
