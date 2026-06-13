"""Email 驗證碼存儲服務"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class VerificationCodeStore:
    """帶過期機制的驗證碼存儲

    支援 Redis 存儲（優先）和內存回退。
    當 Redis 不可用時，自動回退到內存存儲並記錄警告。

    Redis Key 設計：
    - verify:{email} - 驗證碼 (value: 6 位數碼, TTL: 600 秒)
    """

    def __init__(self, ttl_minutes: int = 10, redis_client: aioredis.Redis | None = None):
        """初始化驗證碼存儲

        Args:
            ttl_minutes: 驗證碼過期時間（分鐘）
            redis_client: Redis 連線（可選，不提供時使用純內存模式）
        """
        self._redis: aioredis.Redis | None = redis_client
        self._use_redis: bool = redis_client is not None
        # 內存回退存儲: email -> (code, expires_at)
        self._fallback: dict[str, tuple[str, datetime]] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(minutes=ttl_minutes)
        self._ttl_seconds = ttl_minutes * 60

    async def set_redis(self, redis_client: aioredis.Redis) -> None:
        """設置或更新 Redis 連線

        Args:
            redis_client: Redis 連線
        """
        self._redis = redis_client
        self._use_redis = True
        logger.info("VerificationCodeStore Redis connection configured")

    async def set(self, email: str, code: str) -> None:
        """設置驗證碼，帶過期時間

        Args:
            email: 用戶 Email
            code: 6 位數驗證碼
        """
        key = f"verify:{email.lower()}"

        # 嘗試 Redis
        if self._redis and self._use_redis:
            try:
                await self._redis.set(key, code, ex=self._ttl_seconds)
                logger.debug(f"Verification code stored in Redis for {email}")
                return
            except aioredis.RedisError as e:
                logger.warning(
                    f"Redis unavailable for verification code, falling back to memory: {e}"
                )
                self._use_redis = False

        # 內存回退
        async with self._lock:
            expires_at = datetime.now(UTC) + self._ttl
            self._fallback[email.lower()] = (code, expires_at)
            logger.debug(f"Verification code stored in memory (fallback) for {email}")

    async def get(self, email: str) -> str | None:
        """獲取驗證碼，自動檢查過期

        Args:
            email: 用戶 Email

        Returns:
            驗證碼，如果不存在或已過期返回 None
        """
        key = f"verify:{email.lower()}"

        # 嘗試 Redis
        if self._redis and self._use_redis:
            try:
                return await self._redis.get(key)
            except aioredis.RedisError as e:
                logger.warning(
                    f"Redis unavailable for verification code get, falling back to memory: {e}"
                )
                self._use_redis = False

        # 內存回退
        async with self._lock:
            email_lower = email.lower()
            if email_lower not in self._fallback:
                return None

            code, expires_at = self._fallback[email_lower]

            # 檢查是否過期
            if datetime.now(UTC) > expires_at:
                del self._fallback[email_lower]
                return None

            return code

    async def delete(self, email: str) -> None:
        """刪除驗證碼

        Args:
            email: 用戶 Email
        """
        key = f"verify:{email.lower()}"

        # 嘗試從 Redis 刪除
        if self._redis and self._use_redis:
            try:
                await self._redis.delete(key)
            except aioredis.RedisError as e:
                logger.warning(f"Redis unavailable for verification code delete: {e}")

        # 同時從內存刪除
        async with self._lock:
            self._fallback.pop(email.lower(), None)

    async def cleanup_expired(self) -> int:
        """清理過期的內存驗證碼（Redis 有自動 TTL）

        Returns:
            清理的驗證碼數量
        """
        async with self._lock:
            now = datetime.now(UTC)
            expired_keys = [
                email for email, (_, expires_at) in self._fallback.items() if now > expires_at
            ]

            for email in expired_keys:
                del self._fallback[email]

            if expired_keys:
                logger.info(
                    f"Cleaned up {len(expired_keys)} expired verification codes from memory"
                )

            return len(expired_keys)

    def is_using_redis(self) -> bool:
        """檢查是否正在使用 Redis

        Returns:
            bool: True 如果使用 Redis，False 如果使用內存回退
        """
        return self._use_redis and self._redis is not None


# 驗證碼儲存（10 分鐘過期）
# 初始無 Redis，在 main.py lifespan 中設置
verification_codes = VerificationCodeStore(ttl_minutes=10)
