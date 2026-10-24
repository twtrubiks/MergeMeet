"""Token 全局失效（密碼重置後使舊 Token 失效）單元測試

API 整合（修改密碼後舊 Token 被拒）見 test_auth.py。
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import redis.asyncio as aioredis

from app.services.token_invalidator import INVALIDATION_TTL, TokenInvalidator


@pytest.fixture
def mock_redis(monkeypatch):
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    monkeypatch.setattr(TokenInvalidator, "_redis", redis)
    return redis


@pytest.fixture
def no_redis(monkeypatch):
    monkeypatch.setattr(TokenInvalidator, "_redis", None)


class TestInvalidateAllTokens:
    async def test_records_current_utc_timestamp_with_ttl(self, mock_redis):
        """寫入目前時間戳並帶 TTL（7 天，略長於 refresh token 效期），否則 key 永不過期"""
        before = int(datetime.now(UTC).timestamp())

        await TokenInvalidator.invalidate_all_tokens("user-1")

        after = int(datetime.now(UTC).timestamp())
        [call] = mock_redis.set.await_args_list
        key, value = call.args
        assert key == "token_invalidated:user-1"
        assert before <= int(value) <= after
        assert call.kwargs == {"ex": INVALIDATION_TTL}
        assert INVALIDATION_TTL == 7 * 24 * 60 * 60

    async def test_without_redis_refuses(self, no_redis):
        """沒有 Redis 時無法使舊 Token 失效，必須明確失敗而非假裝成功"""
        with pytest.raises(RuntimeError, match="^Redis is required for token invalidation$"):
            await TokenInvalidator.invalidate_all_tokens("user-1")

    async def test_redis_error_is_logged_not_raised(self, mock_redis):
        mock_redis.set.side_effect = aioredis.RedisError("down")

        await TokenInvalidator.invalidate_all_tokens("user-1")


class TestIsTokenValid:
    async def test_no_record_is_valid(self, mock_redis):
        assert await TokenInvalidator.is_token_valid("user-1", 100) is True
        mock_redis.get.assert_awaited_once_with("token_invalidated:user-1")

    @pytest.mark.parametrize(
        ("token_iat", "expected"),
        [(999, False), (1000, True), (1001, True)],
        ids=["issued-before", "same-second", "issued-after"],
    )
    async def test_compares_issued_at_with_invalidation_time(self, mock_redis, token_iat, expected):
        """失效時間之前簽發的 Token 無效；同一秒內簽發的新 Token 仍有效（iat 以秒為單位）"""
        mock_redis.get.return_value = "1000"

        assert await TokenInvalidator.is_token_valid("user-1", token_iat) is expected

    async def test_without_redis_rejects(self, no_redis):
        assert await TokenInvalidator.is_token_valid("user-1", 100) is False

    async def test_redis_error_rejects(self, mock_redis):
        """Redis 故障時無法確認，安全起見拒絕"""
        mock_redis.get.side_effect = aioredis.RedisError("down")

        assert await TokenInvalidator.is_token_valid("user-1", 100) is False
