"""登入失敗次數限制服務

防止暴力破解攻擊，5 次失敗後鎖定 15 分鐘。

Redis Key 設計：
- login_attempts:{email} - 失敗次數 (integer, TTL: 15分鐘)
- login_lockout:{email} - 鎖定標記 (存在即鎖定, TTL: 15分鐘)
"""
import redis.asyncio as redis
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# 配置常量
MAX_ATTEMPTS = 5           # 最大嘗試次數
LOCKOUT_SECONDS = 900      # 鎖定時間（15 分鐘）
ATTEMPT_WINDOW = 900       # 嘗試計數窗口（15 分鐘）


@dataclass
class LoginAttemptResult:
    """登入嘗試結果

    Attributes:
        is_locked: 是否被鎖定
        remaining_attempts: 剩餘嘗試次數（鎖定時為 0）
        lockout_seconds: 鎖定剩餘秒數（未鎖定時為 0）
    """
    is_locked: bool
    remaining_attempts: int
    lockout_seconds: int


class LoginLimiter:
    """登入限制管理器"""

    def __init__(self, redis_conn: redis.Redis):
        self._redis = redis_conn

    def _get_attempts_key(self, email: str) -> str:
        """獲取嘗試次數的 Redis Key"""
        return f"login_attempts:{email.lower()}"

    def _get_lockout_key(self, email: str) -> str:
        """獲取鎖定狀態的 Redis Key"""
        return f"login_lockout:{email.lower()}"

    async def check_status(self, email: str) -> LoginAttemptResult:
        """檢查登入狀態

        Args:
            email: 用戶 Email

        Returns:
            LoginAttemptResult: 包含鎖定狀態、剩餘次數、鎖定時間
        """
        lockout_key = self._get_lockout_key(email)
        attempts_key = self._get_attempts_key(email)

        # 檢查是否被鎖定
        lockout_ttl = await self._redis.ttl(lockout_key)
        if lockout_ttl > 0:
            return LoginAttemptResult(
                is_locked=True,
                remaining_attempts=0,
                lockout_seconds=lockout_ttl
            )

        # 獲取當前嘗試次數
        attempts = await self._redis.get(attempts_key)
        current_attempts = int(attempts) if attempts else 0
        remaining = max(0, MAX_ATTEMPTS - current_attempts)

        return LoginAttemptResult(
            is_locked=False,
            remaining_attempts=remaining,
            lockout_seconds=0
        )

    async def record_failure(self, email: str) -> LoginAttemptResult:
        """記錄登入失敗

        Args:
            email: 用戶 Email

        Returns:
            LoginAttemptResult: 更新後的狀態
        """
        attempts_key = self._get_attempts_key(email)
        lockout_key = self._get_lockout_key(email)

        # 使用 INCR 原子性增加失敗次數
        new_count = await self._redis.incr(attempts_key)

        # 首次失敗設置 TTL
        if new_count == 1:
            await self._redis.expire(attempts_key, ATTEMPT_WINDOW)

        logger.info(f"Login failure recorded for {email}, attempt {new_count}/{MAX_ATTEMPTS}")

        # 達到上限，觸發鎖定
        if new_count >= MAX_ATTEMPTS:
            await self._redis.setex(lockout_key, LOCKOUT_SECONDS, "1")
            # 清除嘗試計數（鎖定期間不需要）
            await self._redis.delete(attempts_key)
            logger.warning(f"Account locked for {email} due to {new_count} failed attempts")

            return LoginAttemptResult(
                is_locked=True,
                remaining_attempts=0,
                lockout_seconds=LOCKOUT_SECONDS
            )

        return LoginAttemptResult(
            is_locked=False,
            remaining_attempts=MAX_ATTEMPTS - new_count,
            lockout_seconds=0
        )

    async def clear_attempts(self, email: str) -> None:
        """清除登入嘗試記錄（登入成功時調用）

        Args:
            email: 用戶 Email
        """
        attempts_key = self._get_attempts_key(email)
        await self._redis.delete(attempts_key)
        logger.debug(f"Login attempts cleared for {email}")
