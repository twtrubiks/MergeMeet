"""HTTP Security Headers Middleware

為所有響應加上安全相關 HTTP Headers：
- Strict-Transport-Security (HSTS)：強制瀏覽器使用 HTTPS（HTTP 連線下瀏覽器會忽略此 header，開發環境無影響）
- X-Content-Type-Options：防止 MIME 嗅探攻擊
- X-Frame-Options：防止點擊劫持（Clickjacking）
- Referrer-Policy：避免跨站洩漏來源 URL（交友平台隱私考量）
- Content-Security-Policy：API 響應採最嚴格策略；img-src 'self' 允許直接瀏覽 /uploads 圖片

/docs 與 /redoc 不套用 CSP（Swagger UI / ReDoc 需載入 CDN 腳本與 inline script）。
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

# CSP 豁免路徑前綴（API 文件頁面）
CSP_EXEMPT_PREFIXES = ("/docs", "/redoc")

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

CONTENT_SECURITY_POLICY = "default-src 'none'; img-src 'self'; frame-ancestors 'none'"


class SecurityHeadersMiddleware:
    """為所有 HTTP 響應加上安全 Headers 的 Middleware（純 ASGI）"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
                if not path.startswith(CSP_EXEMPT_PREFIXES):
                    headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
            await send(message)

        await self.app(scope, receive, send_wrapper)
