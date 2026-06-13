"""全域 IP 速率限制（slowapi + Redis）

與既有 email-based 防護（LoginLimiter / VerificationLimiter）互補：
- 全域限制：所有 API 端點共用一個 per-IP 計數（application_limits，scope=global）
- 認證端點：登入/註冊/管理員登入另設更嚴格的 per-IP 限制（@limiter.limit 裝飾器，
  由裝飾器獨立計數，不計入全域計數）
- 豁免：/health 健康檢查；/uploads 靜態檔案（Mount 路由不經過 SlowAPIMiddleware）
- Redis 不可用時自動回退內存計數（單實例部署下行為一致）

反向代理注意事項：
get_remote_address 取自 request.client.host。生產環境位於 Nginx 等反向代理後方時，
uvicorn 需以 --proxy-headers --forwarded-allow-ips='<代理 IP>' 啟動，
request.client.host 才會是 X-Forwarded-For 中的真實用戶 IP（直接信任
X-Forwarded-For header 會被偽造，故不在應用層解析）。
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    application_limits=[settings.RATE_LIMIT_GLOBAL],
    storage_uri=settings.REDIS_URL,
    in_memory_fallback_enabled=True,
    headers_enabled=True,  # 注入 X-RateLimit-* 與 Retry-After headers
    enabled=settings.RATE_LIMIT_ENABLED,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """429 回應處理（同步函數：SlowAPIMiddleware 的同步路徑也能使用）"""
    response = JSONResponse(
        {"detail": "請求過於頻繁，請稍後再試"},
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    # 注入 Retry-After / X-RateLimit-* headers
    return request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
