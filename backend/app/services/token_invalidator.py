"""Token 全局失效服務

用於密碼重置等場景，使該用戶所有現有 Token 失效。

Redis Key 設計：
- token_invalidated:{user_id} - 失效時間戳 (Unix timestamp, TTL: 7天)

原理：
- 密碼重置時，記錄當前時間戳
- Token 驗證時，檢查 Token 的 iat 是否早於此時間戳
- 如果 Token 是在失效時間之前創建的，則拒絕
"""
import redis.asyncio as aioredis
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# TTL 設為 7 天（略長於 refresh token 有效期）
INVALIDATION_TTL = 7 * 24 * 60 * 60  # 7 days in seconds


class TokenInvalidator:
    """Token 全局失效管理器"""

    _redis: Optional[aioredis.Redis] = None

    @classmethod
    def set_redis(cls, redis_conn: aioredis.Redis) -> None:
        """設置 Redis 連線"""
        cls._redis = redis_conn
        logger.info("TokenInvalidator Redis connection configured")

    @classmethod
    def _get_key(cls, user_id: str) -> str:
        """獲取 Redis Key"""
        return f"token_invalidated:{user_id}"

    @classmethod
    async def invalidate_all_tokens(cls, user_id: str) -> None:
        """使該用戶所有 Token 失效

        Args:
            user_id: 用戶 ID
        """
        if not cls._redis:
            logger.warning("TokenInvalidator: Redis not configured, skipping invalidation")
            return

        key = cls._get_key(user_id)
        timestamp = int(datetime.now(timezone.utc).timestamp())

        try:
            await cls._redis.setex(key, INVALIDATION_TTL, str(timestamp))
            logger.info(f"All tokens invalidated for user {user_id}")
        except aioredis.RedisError as e:
            logger.error(f"Failed to invalidate tokens for user {user_id}: {e}")

    @classmethod
    async def is_token_valid(cls, user_id: str, token_iat: int) -> bool:
        """檢查 Token 是否有效（未被全局失效）

        Args:
            user_id: 用戶 ID
            token_iat: Token 的 issued at 時間戳

        Returns:
            bool: True 如果 Token 有效，False 如果已被失效
        """
        if not cls._redis:
            # Redis 不可用時，允許 Token（降級處理）
            return True

        key = cls._get_key(user_id)

        try:
            invalidated_at = await cls._redis.get(key)
            if invalidated_at is None:
                # 沒有失效記錄，Token 有效
                return True

            # 如果 Token 是在失效時間之前創建的，則無效
            invalidated_timestamp = int(invalidated_at)
            if token_iat < invalidated_timestamp:
                logger.debug(f"Token rejected for user {user_id}: issued at {token_iat}, invalidated at {invalidated_timestamp}")
                return False

            return True
        except aioredis.RedisError as e:
            logger.warning(f"Failed to check token validity for user {user_id}: {e}")
            # Redis 錯誤時，允許 Token（降級處理）
            return True


# 全局實例（供 main.py 初始化）
token_invalidator = TokenInvalidator()
