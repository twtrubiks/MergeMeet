"""登入失敗次數限制測試

測試 LoginLimiter 服務和登入 API 整合。
"""

from unittest.mock import AsyncMock

import pytest

from app.services.login_limiter import (
    ATTEMPT_WINDOW,
    LOCKOUT_SECONDS,
    MAX_ATTEMPTS,
    LoginAttemptResult,
    LoginLimiter,
)


@pytest.fixture
def mock_redis():
    """Mock Redis 連線"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.ttl = AsyncMock(return_value=-2)  # Key 不存在
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def limiter(mock_redis):
    """建立 LoginLimiter 實例"""
    return LoginLimiter(mock_redis)


class TestLoginLimiter:
    """LoginLimiter 單元測試"""

    @pytest.mark.asyncio
    async def test_check_status_not_locked(self, limiter, mock_redis):
        """測試：未鎖定狀態"""
        result = await limiter.check_status("test@example.com")

        assert result.is_locked is False
        assert result.remaining_attempts == MAX_ATTEMPTS
        assert result.lockout_seconds == 0

    @pytest.mark.asyncio
    async def test_check_status_locked(self, limiter, mock_redis):
        """測試：已鎖定狀態"""
        mock_redis.ttl.return_value = 600  # 還有 10 分鐘

        result = await limiter.check_status("test@example.com")

        assert result.is_locked is True
        assert result.remaining_attempts == 0
        assert result.lockout_seconds == 600

    @pytest.mark.asyncio
    async def test_check_status_with_previous_attempts(self, limiter, mock_redis):
        """測試：有之前的失敗嘗試"""
        mock_redis.get.return_value = "3"  # 已失敗 3 次

        result = await limiter.check_status("test@example.com")

        assert result.is_locked is False
        assert result.remaining_attempts == MAX_ATTEMPTS - 3
        assert result.lockout_seconds == 0

    @pytest.mark.asyncio
    async def test_check_status_locked_with_one_second_left(self, limiter, mock_redis):
        """測試：鎖定只剩 1 秒時仍是鎖定狀態"""
        mock_redis.ttl.return_value = 1

        result = await limiter.check_status("test@example.com")

        assert (result.is_locked, result.lockout_seconds) == (True, 1)

    @pytest.mark.asyncio
    async def test_check_status_remaining_never_negative(self, limiter, mock_redis):
        """測試：失敗次數超過上限（例如鎖定剛過期）時剩餘次數為 0，不會是負數或 1"""
        mock_redis.get.return_value = str(MAX_ATTEMPTS + 2)

        result = await limiter.check_status("test@example.com")

        assert (result.is_locked, result.remaining_attempts) == (False, 0)

    @pytest.mark.asyncio
    async def test_record_failure_first_attempt(self, limiter, mock_redis):
        """測試：記錄第一次失敗"""
        mock_redis.incr.return_value = 1

        result = await limiter.record_failure("test@example.com")

        assert result.is_locked is False
        assert result.remaining_attempts == MAX_ATTEMPTS - 1
        assert result.lockout_seconds == 0
        mock_redis.incr.assert_called_once_with("login_attempts:test@example.com")
        # 首次失敗要設置 TTL（否則計數永不過期，舊的失敗會一直累積）
        mock_redis.expire.assert_called_once_with("login_attempts:test@example.com", ATTEMPT_WINDOW)

    @pytest.mark.asyncio
    async def test_record_failure_subsequent_attempt(self, limiter, mock_redis):
        """測試：記錄後續失敗（非首次）"""
        mock_redis.incr.return_value = 3

        result = await limiter.record_failure("test@example.com")

        assert result.is_locked is False
        assert result.remaining_attempts == MAX_ATTEMPTS - 3
        mock_redis.expire.assert_not_called()  # 非首次不需設置 TTL

    @pytest.mark.asyncio
    async def test_record_failure_triggers_lockout(self, limiter, mock_redis):
        """測試：達到上限觸發鎖定"""
        mock_redis.incr.return_value = MAX_ATTEMPTS

        result = await limiter.record_failure("test@example.com")

        assert result.is_locked is True
        assert result.remaining_attempts == 0
        assert result.lockout_seconds == LOCKOUT_SECONDS
        # 鎖定標記必須寫到 check_status 會檢查的 key，且帶 TTL（否則永久鎖死）
        mock_redis.set.assert_called_once_with(
            "login_lockout:test@example.com", "1", ex=LOCKOUT_SECONDS
        )
        mock_redis.delete.assert_called_once_with("login_attempts:test@example.com")

    @pytest.mark.asyncio
    async def test_clear_attempts(self, limiter, mock_redis):
        """測試：清除嘗試記錄"""
        await limiter.clear_attempts("test@example.com")

        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_case_insensitive(self, limiter, mock_redis):
        """測試：Email 大小寫不敏感"""
        await limiter.check_status("Test@Example.COM")

        # 驗證使用小寫 key
        call_args = mock_redis.ttl.call_args[0][0]
        assert "test@example.com" in call_args


class TestLoginAttemptResult:
    """LoginAttemptResult 資料類測試"""

    def test_dataclass_creation(self):
        """測試：建立結果物件"""
        result = LoginAttemptResult(is_locked=True, remaining_attempts=0, lockout_seconds=900)

        assert result.is_locked is True
        assert result.remaining_attempts == 0
        assert result.lockout_seconds == 900
