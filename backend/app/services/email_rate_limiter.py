"""Email 發送速率限制服務

防止驗證碼/密碼重置郵件濫發，60 秒冷卻 + 每日上限 5 次。

Redis Key 設計：
- email_rate:{email}:cooldown - 冷卻標記 (存在即冷卻中, TTL: 60秒)
- email_rate:{email}:count - 今日發送次數 (integer, TTL: 到 UTC 午夜)
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# 配置常量
COOLDOWN_SECONDS = 60  # 兩次發送間的冷卻時間
MAX_DAILY_SENDS = 5  # 每日發送上限


@dataclass
class EmailRateLimitResult:
    """Email 速率限制檢查結果

    Attributes:
        allowed: 是否允許發送
        cooldown_seconds: 冷卻剩餘秒數（冷卻中才有值）
        daily_limit_reached: 是否達到每日上限
    """

    allowed: bool
    cooldown_seconds: int = 0
    daily_limit_reached: bool = False


def _seconds_until_utc_midnight() -> int:
    """計算距離 UTC 午夜的秒數（作為每日計數的 TTL）"""
    now = datetime.now(UTC)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((midnight - now).total_seconds()))


class EmailRateLimiter:
    """Email 發送速率限制管理器"""

    def __init__(self, redis_conn: redis.Redis):
        self._redis = redis_conn

    def _get_cooldown_key(self, email: str) -> str:
        """獲取冷卻標記的 Redis Key"""
        return f"email_rate:{email.lower()}:cooldown"

    def _get_count_key(self, email: str) -> str:
        """獲取今日計數的 Redis Key"""
        return f"email_rate:{email.lower()}:count"

    async def check_and_record(self, email: str) -> EmailRateLimitResult:
        """檢查速率限制並記錄本次發送

        規則:
        - 60 秒內只能發送 1 次
        - 每天（UTC）最多發送 5 次

        Args:
            email: 用戶 Email

        Returns:
            EmailRateLimitResult: 不允許時帶有原因（冷卻中或達每日上限）
        """
        cooldown_key = self._get_cooldown_key(email)
        count_key = self._get_count_key(email)

        # 檢查 60 秒冷卻期
        cooldown_ttl = await self._redis.ttl(cooldown_key)
        if cooldown_ttl > 0:
            return EmailRateLimitResult(allowed=False, cooldown_seconds=cooldown_ttl)

        # 使用 INCR 原子性增加今日計數（超限後的嘗試也計入，不影響結果）
        new_count = await self._redis.incr(count_key)

        # 首次計數設置 TTL 到 UTC 午夜（隔日自動重置）
        if new_count == 1:
            await self._redis.expire(count_key, _seconds_until_utc_midnight())

        # 達到每日上限
        if new_count > MAX_DAILY_SENDS:
            logger.info(f"Email daily rate limit reached for {email}")
            return EmailRateLimitResult(allowed=False, daily_limit_reached=True)

        # 允許發送，記錄冷卻標記
        await self._redis.setex(cooldown_key, COOLDOWN_SECONDS, "1")
        return EmailRateLimitResult(allowed=True)
