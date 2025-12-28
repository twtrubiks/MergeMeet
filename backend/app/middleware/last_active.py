"""用戶活躍時間更新 Middleware

在每個已認證請求成功後自動更新 Profile.last_active，
讓配對算法的活躍度評分能正常運作。
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.profile import Profile

logger = logging.getLogger(__name__)

# 可覆寫的 session factory（用於測試）
_session_factory: Optional[async_sessionmaker] = None


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


class LastActiveMiddleware(BaseHTTPMiddleware):
    """更新用戶最後活躍時間的 Middleware

    設計考量：
    1. 使用獨立的 DB session（避免影響請求的事務）
    2. 錯誤靜默處理（不影響原請求）
    3. 僅在請求成功（2xx）時更新
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 先執行請求
        response = await call_next(request)

        # 請求成功後（2xx），嘗試更新 last_active
        if 200 <= response.status_code < 300:
            user_id = self._extract_user_id(request)
            if user_id:
                await self._update_last_active(user_id)

        return response

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """從請求中提取 user_id

        支援兩種認證模式：
        1. Cookie 認證：從 access_token cookie 讀取
        2. Bearer Token：從 Authorization header 讀取
        """
        token = None

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

    async def _update_last_active(self, user_id: str) -> None:
        """更新用戶的 last_active 時間

        使用獨立 session，錯誤靜默處理。
        """
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                await session.execute(
                    update(Profile)
                    .where(Profile.user_id == UUID(user_id))
                    .values(last_active=datetime.now(timezone.utc))
                )
                await session.commit()
                logger.debug(f"Updated last_active for user {user_id}")
        except Exception as e:
            # 錯誤靜默處理，不影響原請求
            logger.warning(f"Failed to update last_active for user {user_id}: {e}")
