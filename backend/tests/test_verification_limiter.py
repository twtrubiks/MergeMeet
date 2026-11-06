"""驗證碼嘗試次數限制測試

測試 VerificationLimiter 服務和 /api/auth/verify-email 整合（暴力破解 6 位數驗證碼的防護）。
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.services.redis_client import get_redis
from app.services.verification_code import verification_codes
from app.services.verification_limiter import (
    ATTEMPT_WINDOW,
    LOCKOUT_SECONDS,
    MAX_VERIFY_ATTEMPTS,
    VerificationLimiter,
)


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.ttl = AsyncMock(return_value=-2)  # Key 不存在
    redis.incr = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def limiter(mock_redis):
    return VerificationLimiter(mock_redis)


class TestVerificationLimiter:
    async def test_check_status_not_locked(self, limiter, mock_redis):
        result = await limiter.check_status("Test@Example.com")

        assert (result.is_locked, result.remaining_attempts, result.lockout_seconds) == (
            False,
            MAX_VERIFY_ATTEMPTS,
            0,
        )
        mock_redis.ttl.assert_awaited_once_with("verify_lockout:test@example.com")
        mock_redis.get.assert_awaited_once_with("verify_attempts:test@example.com")

    async def test_check_status_locked_with_one_second_left(self, limiter, mock_redis):
        mock_redis.ttl.return_value = 1

        result = await limiter.check_status("test@example.com")

        assert (result.is_locked, result.remaining_attempts, result.lockout_seconds) == (
            True,
            0,
            1,
        )

    async def test_check_status_with_previous_attempts(self, limiter, mock_redis):
        mock_redis.get.return_value = "3"

        result = await limiter.check_status("test@example.com")

        assert (result.is_locked, result.remaining_attempts) == (False, MAX_VERIFY_ATTEMPTS - 3)

    async def test_check_status_remaining_never_negative(self, limiter, mock_redis):
        mock_redis.get.return_value = str(MAX_VERIFY_ATTEMPTS + 2)

        result = await limiter.check_status("test@example.com")

        assert (result.is_locked, result.remaining_attempts) == (False, 0)

    async def test_first_failure_sets_window_ttl(self, limiter, mock_redis):
        """首次失敗要設置 TTL，否則計數永不過期，舊的失敗會一直累積"""
        result = await limiter.record_failure("Test@Example.com")

        assert (result.is_locked, result.remaining_attempts, result.lockout_seconds) == (
            False,
            MAX_VERIFY_ATTEMPTS - 1,
            0,
        )
        mock_redis.incr.assert_awaited_once_with("verify_attempts:test@example.com")
        mock_redis.expire.assert_awaited_once_with(
            "verify_attempts:test@example.com", ATTEMPT_WINDOW
        )

    async def test_later_failure_keeps_window(self, limiter, mock_redis):
        """後續失敗不重設 TTL（否則每次失敗都延長計數窗口）"""
        mock_redis.incr.return_value = 2

        result = await limiter.record_failure("test@example.com")

        assert (result.is_locked, result.remaining_attempts) == (False, MAX_VERIFY_ATTEMPTS - 2)
        mock_redis.expire.assert_not_awaited()
        mock_redis.set.assert_not_awaited()

    async def test_last_allowed_failure_not_locked(self, limiter, mock_redis):
        mock_redis.incr.return_value = MAX_VERIFY_ATTEMPTS - 1

        result = await limiter.record_failure("test@example.com")

        assert (result.is_locked, result.remaining_attempts) == (False, 1)

    async def test_reaching_limit_locks(self, limiter, mock_redis):
        """達到上限：寫入帶 TTL 的鎖定標記（否則永久鎖死），並清除計數"""
        mock_redis.incr.return_value = MAX_VERIFY_ATTEMPTS

        result = await limiter.record_failure("test@example.com")

        assert (result.is_locked, result.remaining_attempts, result.lockout_seconds) == (
            True,
            0,
            LOCKOUT_SECONDS,
        )
        mock_redis.set.assert_awaited_once_with(
            "verify_lockout:test@example.com", "1", ex=LOCKOUT_SECONDS
        )
        mock_redis.delete.assert_awaited_once_with("verify_attempts:test@example.com")

    async def test_clear_attempts(self, limiter, mock_redis):
        await limiter.clear_attempts("Test@Example.com")

        mock_redis.delete.assert_awaited_once_with("verify_attempts:test@example.com")


async def test_verify_email_counts_down_then_locks(client: AsyncClient):
    """錯誤驗證碼逐次扣減剩餘次數，第 5 次鎖定，鎖定後正確驗證碼也被擋下"""
    email = f"verify_limit_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123", "date_of_birth": "1995-01-01"},
    )
    code = await verification_codes.get(email)
    wrong = "000000" if code != "000000" else "111111"

    remaining = []
    for _ in range(MAX_VERIFY_ATTEMPTS - 1):
        response = await client.post(
            "/api/auth/verify-email", json={"email": email, "verification_code": wrong}
        )
        assert response.status_code == 400
        remaining.append(response.headers["X-RateLimit-Remaining"])
    assert remaining == ["4", "3", "2", "1"]
    assert response.json()["detail"] == "驗證碼錯誤，剩餘 1 次嘗試機會"

    response = await client.post(
        "/api/auth/verify-email", json={"email": email, "verification_code": wrong}
    )
    assert response.status_code == 429
    assert response.headers["X-Lockout-Seconds"] == str(LOCKOUT_SECONDS)

    response = await client.post(
        "/api/auth/verify-email", json={"email": email, "verification_code": code}
    )
    assert response.status_code == 429


async def test_verify_email_success_clears_attempts(client: AsyncClient):
    """驗證成功後清除失敗計數"""
    email = f"verify_clear_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123", "date_of_birth": "1995-01-01"},
    )
    code = await verification_codes.get(email)
    wrong = "000000" if code != "000000" else "111111"
    await client.post("/api/auth/verify-email", json={"email": email, "verification_code": wrong})

    response = await client.post(
        "/api/auth/verify-email", json={"email": email, "verification_code": code}
    )

    assert response.status_code == 200
    redis_conn = await get_redis()
    assert await redis_conn.get(f"verify_attempts:{email}") is None
