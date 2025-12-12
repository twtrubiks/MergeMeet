"""Redis 客戶端服務

提供 Redis 連線管理和通用操作封裝。
用於登入限制、快取等功能。
"""
import redis.asyncio as redis
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客戶端管理器

    使用單例模式管理 Redis 連線池。
    """

    _instance: Optional["RedisClient"] = None
    _pool: Optional[redis.ConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_connection(self) -> redis.Redis:
        """獲取 Redis 連線

        Returns:
            redis.Redis: Redis 連線實例
        """
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Redis connection pool created: {settings.REDIS_URL}")
        return redis.Redis(connection_pool=self._pool)

    async def close(self):
        """關閉連線池"""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            logger.info("Redis connection pool closed")


# 全局單例
redis_client = RedisClient()


async def get_redis() -> redis.Redis:
    """依賴注入用的 Redis 連線獲取函數"""
    return await redis_client.get_connection()
