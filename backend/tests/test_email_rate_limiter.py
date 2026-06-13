"""Email 發送速率限制測試

測試 EmailRateLimiter 服務。
"""

from unittest.mock import AsyncMock

import pytest

from app.services.email_rate_limiter import (
    COOLDOWN_SECONDS,
    MAX_DAILY_SENDS,
    EmailRateLimiter,
    _seconds_until_utc_midnight,
)


@pytest.fixture
def mock_redis():
    """Mock Redis 連線"""
    redis = AsyncMock()
    redis.ttl = AsyncMock(return_value=-2)  # Key 不存在
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def limiter(mock_redis):
    """建立 EmailRateLimiter 實例"""
    return EmailRateLimiter(mock_redis)


class TestEmailRateLimiter:
    """EmailRateLimiter 單元測試"""

    @pytest.mark.asyncio
    async def test_first_send_allowed(self, limiter, mock_redis):
        """測試：首次發送允許，並設置計數 TTL 與冷卻標記"""
        result = await limiter.check_and_record("test@example.com")

        assert result.allowed is True
        assert result.cooldown_seconds == 0
        assert result.daily_limit_reached is False
        mock_redis.expire.assert_called_once()  # 首次計數設置 TTL 到午夜
        mock_redis.set.assert_called_once()  # 記錄 60 秒冷卻
        assert mock_redis.set.call_args.kwargs["ex"] == COOLDOWN_SECONDS

    @pytest.mark.asyncio
    async def test_cooldown_blocks_send(self, limiter, mock_redis):
        """測試：冷卻期內拒絕發送，回報剩餘秒數"""
        mock_redis.ttl.return_value = 30

        result = await limiter.check_and_record("test@example.com")

        assert result.allowed is False
        assert result.cooldown_seconds == 30
        assert result.daily_limit_reached is False
        mock_redis.incr.assert_not_called()  # 冷卻中不計入今日次數

    @pytest.mark.asyncio
    async def test_daily_limit_reached(self, limiter, mock_redis):
        """測試：達到每日上限拒絕發送，且不記錄冷卻"""
        mock_redis.incr.return_value = MAX_DAILY_SENDS + 1

        result = await limiter.check_and_record("test@example.com")

        assert result.allowed is False
        assert result.daily_limit_reached is True
        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_subsequent_send_keeps_count_ttl(self, limiter, mock_redis):
        """測試：非首次發送不重設計數 TTL"""
        mock_redis.incr.return_value = 2

        result = await limiter.check_and_record("test@example.com")

        assert result.allowed is True
        mock_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_case_insensitive(self, limiter, mock_redis):
        """測試：Email 大小寫不敏感（Key 統一小寫）"""
        await limiter.check_and_record("Test@Example.com")

        assert mock_redis.incr.call_args[0][0] == "email_rate:test@example.com:count"


def test_seconds_until_utc_midnight_range():
    """測試：距 UTC 午夜秒數在合理範圍內"""
    seconds = _seconds_until_utc_midnight()
    assert 1 <= seconds <= 86400
