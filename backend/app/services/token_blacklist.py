"""Token 黑名單服務

用於在登出時將 Token 加入黑名單，防止已登出的 Token 被繼續使用。

注意：目前使用內存存儲，伺服器重啟後黑名單會清空。

Redis 整合備註（暫未使用）：
- 生產環境建議整合 Redis 實現持久化和分散式支援
- 可使用 redis.setex(f"blacklist:{token}", ttl, "1") 自動過期
- 支援多實例部署時的黑名單共享
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """Token 黑名單管理器

    使用內存字典存儲已登出的 Token，並自動清理過期的記錄。

    Attributes:
        _blacklist: 儲存 token -> 過期時間 的映射
        _lock: 並發安全鎖
    """

    def __init__(self):
        # Token -> 過期時間（過期後自動移除）
        self._blacklist: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def add(self, token: str, expires_at: datetime) -> None:
        """將 Token 加入黑名單

        Args:
            token: JWT Token
            expires_at: Token 的原始過期時間（用於自動清理）
        """
        async with self._lock:
            self._blacklist[token] = expires_at
            logger.info(f"Token added to blacklist, expires at {expires_at}")

    async def is_blacklisted(self, token: str) -> bool:
        """檢查 Token 是否在黑名單中

        Args:
            token: JWT Token

        Returns:
            bool: True 如果在黑名單中
        """
        async with self._lock:
            if token in self._blacklist:
                # 檢查是否已過期（過期的 Token 可以從黑名單移除）
                expires_at = self._blacklist[token]
                if expires_at < datetime.now(timezone.utc):
                    # Token 已過期，從黑名單移除
                    del self._blacklist[token]
                    return False
                return True
            return False

    async def remove(self, token: str) -> bool:
        """從黑名單移除 Token（通常用於測試）

        Args:
            token: JWT Token

        Returns:
            bool: True 如果成功移除
        """
        async with self._lock:
            if token in self._blacklist:
                del self._blacklist[token]
                return True
            return False

    async def cleanup_expired(self) -> int:
        """清理已過期的 Token

        Returns:
            int: 清理的 Token 數量
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_tokens = [
                token for token, expires_at in self._blacklist.items()
                if expires_at < now
            ]

            for token in expired_tokens:
                del self._blacklist[token]

            if expired_tokens:
                logger.info(f"Cleaned up {len(expired_tokens)} expired tokens from blacklist")

            return len(expired_tokens)

    async def start_cleanup_task(self):
        """啟動定期清理任務"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("Started token blacklist cleanup task")

    async def _periodic_cleanup(self):
        """定期清理過期 Token（每 5 分鐘執行一次）"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 分鐘
                await self.cleanup_expired()
            except asyncio.CancelledError:
                logger.info("Token blacklist cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in token blacklist cleanup: {e}", exc_info=True)

    async def get_blacklist_size(self) -> int:
        """獲取黑名單大小（用於監控）

        Returns:
            int: 黑名單中的 Token 數量
        """
        async with self._lock:
            return len(self._blacklist)


# 全局單例實例
token_blacklist = TokenBlacklist()
