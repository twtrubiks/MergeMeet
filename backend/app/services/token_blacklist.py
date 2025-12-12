"""Token 黑名單服務

用於在登出時將 Token 加入黑名單，防止已登出的 Token 被繼續使用。

支援 Redis 存儲（生產環境推薦）和內存回退（Redis 不可用時自動切換）。

Redis Key 設計：
- blacklist:{token_hash} - Token 黑名單標記 (value: "1", TTL: Token 剩餘有效期)
- 使用 SHA256 hash 縮短 Key（原始 JWT 約 300+ 字元）
"""
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """Token 黑名單管理器

    支援 Redis 存儲（優先）和內存回退。
    當 Redis 不可用時，自動回退到內存存儲並記錄警告。

    Attributes:
        _redis: Redis 連線（可選）
        _use_redis: Redis 是否可用的標記
        _fallback: 內存回退存儲
        _lock: 並發安全鎖
    """

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        """初始化 Token 黑名單管理器

        Args:
            redis_client: Redis 連線（可選，不提供時使用純內存模式）
        """
        self._redis: Optional[aioredis.Redis] = redis_client
        self._use_redis: bool = redis_client is not None
        # 內存回退存儲: token -> 過期時間
        self._fallback: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def set_redis(self, redis_client: aioredis.Redis) -> None:
        """設置或更新 Redis 連線

        Args:
            redis_client: Redis 連線
        """
        self._redis = redis_client
        self._use_redis = True
        logger.info("Token blacklist Redis connection configured")

    @staticmethod
    def _hash_token(token: str) -> str:
        """將 Token 轉為短 hash（避免 Redis Key 過長）

        Args:
            token: JWT Token

        Returns:
            str: 32 字元的 SHA256 hash
        """
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    async def add(self, token: str, expires_at: datetime) -> None:
        """將 Token 加入黑名單

        Args:
            token: JWT Token
            expires_at: Token 的原始過期時間（用於計算 TTL）
        """
        # 計算 TTL（秒）
        ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        if ttl <= 0:
            # Token 已過期，無需加入黑名單
            logger.debug("Token already expired, skipping blacklist")
            return

        token_hash = self._hash_token(token)

        # 嘗試 Redis
        if self._redis and self._use_redis:
            try:
                await self._redis.setex(f"blacklist:{token_hash}", ttl, "1")
                logger.info(f"Token added to Redis blacklist, TTL: {ttl}s")
                return
            except aioredis.RedisError as e:
                logger.warning(f"Redis unavailable for blacklist add, falling back to memory: {e}")
                self._use_redis = False

        # 內存回退
        async with self._lock:
            self._fallback[token] = expires_at
            logger.info(f"Token added to memory blacklist (fallback), expires at {expires_at}")

    async def is_blacklisted(self, token: str) -> bool:
        """檢查 Token 是否在黑名單中

        Args:
            token: JWT Token

        Returns:
            bool: True 如果在黑名單中
        """
        token_hash = self._hash_token(token)

        # 嘗試 Redis
        if self._redis and self._use_redis:
            try:
                result = await self._redis.exists(f"blacklist:{token_hash}")
                return result > 0
            except aioredis.RedisError as e:
                logger.warning(
                    f"Redis unavailable for blacklist check, "
                    f"falling back to memory: {e}"
                )
                self._use_redis = False

        # 內存回退檢查
        async with self._lock:
            if token in self._fallback:
                expires_at = self._fallback[token]
                if expires_at < datetime.now(timezone.utc):
                    # Token 已過期，從內存移除
                    del self._fallback[token]
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
        token_hash = self._hash_token(token)
        removed = False

        # 嘗試從 Redis 移除
        if self._redis and self._use_redis:
            try:
                result = await self._redis.delete(f"blacklist:{token_hash}")
                removed = result > 0
            except aioredis.RedisError as e:
                logger.warning(f"Redis unavailable for blacklist remove: {e}")

        # 同時從內存移除
        async with self._lock:
            if token in self._fallback:
                del self._fallback[token]
                removed = True

        return removed

    async def cleanup_expired(self) -> int:
        """清理已過期的內存 Token（Redis 有自動 TTL）

        Returns:
            int: 清理的 Token 數量
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_tokens = [
                token for token, expires_at in self._fallback.items()
                if expires_at < now
            ]

            for token in expired_tokens:
                del self._fallback[token]

            if expired_tokens:
                logger.info(
                    f"Cleaned up {len(expired_tokens)} expired tokens "
                    f"from memory blacklist"
                )

            return len(expired_tokens)

    async def start_cleanup_task(self):
        """啟動定期清理任務（用於內存回退時的清理）"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("Started token blacklist cleanup task")

    async def stop_cleanup_task(self):
        """停止定期清理任務"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped token blacklist cleanup task")

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
            int: 黑名單中的 Token 數量（僅計算內存，Redis 需另行查詢）
        """
        async with self._lock:
            return len(self._fallback)

    def is_using_redis(self) -> bool:
        """檢查是否正在使用 Redis

        Returns:
            bool: True 如果使用 Redis，False 如果使用內存回退
        """
        return self._use_redis and self._redis is not None


# 全局單例實例（初始無 Redis，在 main.py lifespan 中設置）
token_blacklist = TokenBlacklist()
