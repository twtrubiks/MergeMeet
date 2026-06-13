"""用戶活躍時間更新 Middleware

在每個已認證請求成功後自動更新 Profile.last_active，
讓配對算法的活躍度評分能正常運作。
"""

import contextlib
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.profile import Profile
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

# 可覆寫的 session factory（用於測試）
_session_factory: async_sessionmaker | None = None

# 節流設定（秒），0 表示不節流
_throttle_seconds: int = 300


def set_session_factory(factory: async_sessionmaker) -> None:
    """設置 session factory（用於測試）"""
    global _session_factory
    _session_factory = factory


def reset_session_factory() -> None:
    """重置 session factory"""
    global _session_factory
    _session_factory = None


def get_session_factory() -> async_sessionmaker:
    """取得 session factory"""
    return _session_factory or AsyncSessionLocal


def set_throttle_seconds(seconds: int) -> None:
    """設置節流秒數（用於測試，0 表示不節流）"""
    global _throttle_seconds
    _throttle_seconds = seconds


def reset_throttle_seconds() -> None:
    """重置節流秒數為預設值（300 秒）"""
    global _throttle_seconds
    _throttle_seconds = 300


class LastActiveMiddleware:
    """更新用戶最後活躍時間的 Middleware（純 ASGI）

    設計考量：
    1. 使用純 ASGI middleware（避免 BaseHTTPMiddleware 的 anyio task 開銷）
    2. 使用 Redis 節流（同一用戶 5 分鐘內只更新一次 DB）
    3. 使用獨立的 DB session（避免影響請求的事務）
    4. 錯誤靜默處理（不影響原請求）
    5. 僅在請求成功（2xx）時更新
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code: int | None = None

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # 請求成功後（2xx），嘗試更新 last_active
        if status_code and 200 <= status_code < 300:
            request = Request(scope)
            user_id = _extract_user_id(request)
            if user_id:
                await _throttled_update(user_id)


def _extract_user_id(request: Request) -> str | None:
    """從請求中提取 user_id

    支援兩種認證模式：
    1. Cookie 認證：從 access_token cookie 讀取
    2. Bearer Token：從 Authorization header 讀取
    """
    # 優先嘗試 Cookie
    token = request.cookies.get("access_token")

    # 回退到 Bearer Token
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    # 解碼 Token（僅提取 user_id）
    try:
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            return payload.get("sub")
    except Exception:
        pass

    return None


async def _throttled_update(user_id: str) -> None:
    """節流更新 last_active（同一用戶在節流時間內只更新一次 DB）

    使用 Redis 記錄最近更新時間，避免高頻端點產生大量 DB 寫入。
    Redis 不可用時降級為每次更新（維持原有行為）。
    """
    conn = None
    redis_key = f"last_active:{user_id}"

    # 嘗試 Redis 節流檢查
    if _throttle_seconds > 0:
        try:
            conn = await redis_client.get_connection()
            if await conn.get(redis_key):
                return
        except Exception:
            conn = None

    # 更新 DB
    await _update_last_active(user_id)

    # 更新成功後設置節流 key
    if conn:
        with contextlib.suppress(Exception):
            await conn.set(redis_key, "1", ex=_throttle_seconds)


async def _update_last_active(user_id: str) -> None:
    """更新用戶的 last_active 時間

    使用獨立 session，錯誤靜默處理。
    """
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(
                update(Profile)
                .where(Profile.user_id == UUID(user_id))
                .values(last_active=datetime.now(UTC))
            )
            await session.commit()
            logger.debug(f"Updated last_active for user {user_id}")
    except Exception as e:
        # 錯誤靜默處理，不影響原請求
        logger.warning(f"Failed to update last_active for user {user_id}: {e}")
