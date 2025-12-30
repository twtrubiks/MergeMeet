"""驗證碼存儲測試"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from app.api.auth import VerificationCodeStore


class TestVerificationCodeStore:
    """驗證碼存儲單元測試（內存模式）"""

    @pytest.fixture
    def store(self):
        """建立新的驗證碼存儲實例（無 Redis）"""
        return VerificationCodeStore(ttl_minutes=10)

    @pytest.mark.asyncio
    async def test_set_and_get_code(self, store):
        """測試設置和獲取驗證碼"""
        email = "test@example.com"
        code = "123456"

        await store.set(email, code)
        result = await store.get(email)

        assert result == code

    @pytest.mark.asyncio
    async def test_get_nonexistent_code(self, store):
        """測試獲取不存在的驗證碼"""
        result = await store.get("nonexistent@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_code(self, store):
        """測試刪除驗證碼"""
        email = "delete@example.com"
        code = "654321"

        await store.set(email, code)
        assert await store.get(email) == code

        await store.delete(email)
        assert await store.get(email) is None

    @pytest.mark.asyncio
    async def test_email_case_insensitive(self, store):
        """測試 Email 大小寫不敏感"""
        email_upper = "TEST@EXAMPLE.COM"
        email_lower = "test@example.com"
        code = "111222"

        await store.set(email_upper, code)

        # 用小寫應該也能取到
        result = await store.get(email_lower)
        assert result == code

    @pytest.mark.asyncio
    async def test_overwrite_code(self, store):
        """測試覆蓋舊驗證碼"""
        email = "overwrite@example.com"
        old_code = "111111"
        new_code = "222222"

        await store.set(email, old_code)
        await store.set(email, new_code)

        result = await store.get(email)
        assert result == new_code

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, store):
        """測試清理過期驗證碼"""
        # 手動加入過期的驗證碼
        expired_email = "expired@example.com"
        store._fallback[expired_email] = ("123456", datetime.now(timezone.utc) - timedelta(seconds=1))

        valid_email = "valid@example.com"
        await store.set(valid_email, "654321")

        cleaned = await store.cleanup_expired()
        assert cleaned == 1

        assert await store.get(expired_email) is None
        assert await store.get(valid_email) == "654321"


class TestVerificationCodeStoreWithRedis:
    """驗證碼存儲 Redis 模式測試"""

    @pytest.mark.asyncio
    async def test_set_code_to_redis(self, mock_redis):
        """測試：驗證碼存入 Redis"""
        store = VerificationCodeStore(ttl_minutes=10, redis_client=mock_redis)
        email = "redis_test@example.com"
        code = "123456"

        await store.set(email, code)

        # 驗證 Redis setex 被調用
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == f"verify:{email.lower()}"
        assert call_args[1] == 600  # 10 分鐘
        assert call_args[2] == code

    @pytest.mark.asyncio
    async def test_get_code_from_redis(self, mock_redis):
        """測試：從 Redis 獲取驗證碼"""
        store = VerificationCodeStore(ttl_minutes=10, redis_client=mock_redis)
        email = "redis_get@example.com"
        code = "654321"

        await store.set(email, code)
        result = await store.get(email)

        assert result == code
        assert store.is_using_redis() is True

    @pytest.mark.asyncio
    async def test_delete_from_redis(self, mock_redis):
        """測試：從 Redis 刪除驗證碼"""
        store = VerificationCodeStore(ttl_minutes=10, redis_client=mock_redis)
        email = "redis_delete@example.com"
        code = "111222"

        await store.set(email, code)
        await store.delete(email)

        mock_redis.delete.assert_called_with(f"verify:{email.lower()}")


class TestVerificationCodeStoreFallback:
    """驗證碼存儲回退測試（Redis 不可用時）"""

    @pytest.mark.asyncio
    async def test_fallback_on_redis_error_set(self, mock_redis_error):
        """測試：Redis 錯誤時回退到內存（set）"""
        store = VerificationCodeStore(ttl_minutes=10, redis_client=mock_redis_error)
        email = "fallback@example.com"
        code = "999888"

        # 應該不會拋出錯誤，而是回退到內存
        await store.set(email, code)

        # 驗證 _use_redis 被設為 False
        assert store._use_redis is False
        # 驗證碼在內存中
        assert email.lower() in store._fallback

    @pytest.mark.asyncio
    async def test_fallback_on_redis_error_get(self, mock_redis_error):
        """測試：Redis 錯誤時回退到內存（get）"""
        store = VerificationCodeStore(ttl_minutes=10, redis_client=mock_redis_error)
        email = "fallback_get@example.com"
        code = "777666"

        # 先手動加入內存
        store._fallback[email.lower()] = (code, datetime.now(timezone.utc) + timedelta(minutes=10))

        # 獲取時會嘗試 Redis，失敗後回退到內存
        result = await store.get(email)

        assert result == code
        assert store._use_redis is False

    @pytest.mark.asyncio
    async def test_set_redis_enables_redis_mode(self):
        """測試：set_redis 啟用 Redis 模式"""
        store = VerificationCodeStore(ttl_minutes=10)  # 初始無 Redis
        assert store.is_using_redis() is False

        mock_redis = AsyncMock()
        await store.set_redis(mock_redis)

        assert store.is_using_redis() is True

    @pytest.mark.asyncio
    async def test_delete_clears_both_redis_and_memory(self, mock_redis):
        """測試：刪除同時清除 Redis 和內存"""
        store = VerificationCodeStore(ttl_minutes=10, redis_client=mock_redis)
        email = "both_delete@example.com"
        code = "555444"

        # 先加入 Redis
        await store.set(email, code)
        # 手動加入內存
        store._fallback[email.lower()] = (code, datetime.now(timezone.utc) + timedelta(minutes=10))

        await store.delete(email)

        # 兩邊都應該被清除
        mock_redis.delete.assert_called()
        assert email.lower() not in store._fallback
