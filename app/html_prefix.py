from __future__ import annotations

import re
from typing import Optional


_ATTR_RE = re.compile(
    r"""\b(href|src)=(["'])(/[^"']*)\2""",
    re.IGNORECASE,
)
_FETCH_API_RE = re.compile(
    r"""fetch\(\s*(["'])(/api/[^"']*)\1""",
)


def rewrite_html(html: str, prefix: str) -> str:
    """Inject __FGB_BASE__ and prefix root-absolute href/src/fetch paths."""
    if not prefix or not html:
        return html

    marker = '__FGB_BASE__="%s"' % prefix
    if marker not in html and ("__FGB_BASE__='%s'" % prefix) not in html:
        inject = '<script>window.__FGB_BASE__="%s";</script>\n' % prefix
        lower = html.lower()
        idx = lower.find("<head>")
        if idx >= 0:
            insert_at = idx + len("<head>")
            html = html[:insert_at] + "\n" + inject + html[insert_at:]
        else:
            html = inject + html

    def attr_sub(match: re.Match) -> str:
        attr, quote, path = match.group(1), match.group(2), match.group(3)
        if path.startswith("//"):
            return match.group(0)
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
            return match.group(0)
        return "%s=%s%s%s%s" % (attr, quote, prefix, path, quote)

    html = _ATTR_RE.sub(attr_sub, html)

    def fetch_sub(match: re.Match) -> str:
        quote, path = match.group(1), match.group(2)
        if path.startswith(prefix + "/"):
            return match.group(0)
        return "fetch(%s%s%s%s" % (quote, prefix, path, quote)

    html = _FETCH_API_RE.sub(fetch_sub, html)
    return html


async def read_response_body(response) -> bytes:
    body = b""
    async for chunk in response.body_iterator:
        if isinstance(chunk, str):
            body += chunk.encode("utf-8")
        else:
            body += chunk
    return body
