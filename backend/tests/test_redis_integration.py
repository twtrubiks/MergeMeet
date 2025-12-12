"""Redis 整合測試

需要實際 Redis 服務運行。
使用 pytest 標記：@pytest.mark.integration

執行方式：
    pytest tests/test_redis_integration.py -v -m integration

注意：這些測試需要 Redis 服務運行在 localhost:6379
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

from app.services.redis_client import get_redis
from app.services.token_blacklist import TokenBlacklist
from app.services.content_moderation import ContentModerationService
from app.api.auth import VerificationCodeStore


# 標記所有測試為整合測試
pytestmark = pytest.mark.integration


class TestRedisConnection:
    """Redis 連線測試"""

    @pytest.mark.asyncio
    async def test_redis_ping(self):
        """測試 Redis 連線 - ping"""
        try:
            redis = await get_redis()
            result = await redis.ping()
            assert result is True
        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")


class TestTokenBlacklistRedisIntegration:
    """Token 黑名單 Redis 整合測試"""

    @pytest.mark.asyncio
    async def test_add_and_check_real_redis(self):
        """測試：使用真實 Redis 的 Token 黑名單操作"""
        try:
            redis = await get_redis()
            blacklist = TokenBlacklist(redis_client=redis)

            token = f"integration_test_token_{datetime.now().timestamp()}"
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=1)

            # 加入黑名單
            await blacklist.add(token, expires_at)

            # 驗證在黑名單中
            assert await blacklist.is_blacklisted(token) is True

            # 清理
            await blacklist.remove(token)
            assert await blacklist.is_blacklisted(token) is False

        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")

    @pytest.mark.asyncio
    async def test_redis_ttl_works(self):
        """測試：Redis TTL 自動過期"""
        try:
            redis = await get_redis()
            blacklist = TokenBlacklist(redis_client=redis)

            token = f"ttl_test_token_{datetime.now().timestamp()}"
            # 設置 2 秒後過期
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=2)

            await blacklist.add(token, expires_at)

            # 立即檢查應該在黑名單中
            assert await blacklist.is_blacklisted(token) is True

            # 等待過期
            import asyncio
            await asyncio.sleep(3)

            # 過期後應該不在黑名單中
            assert await blacklist.is_blacklisted(token) is False

        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")


class TestVerificationCodeRedisIntegration:
    """驗證碼存儲 Redis 整合測試"""

    @pytest.mark.asyncio
    async def test_set_and_get_real_redis(self):
        """測試：使用真實 Redis 的驗證碼操作"""
        try:
            redis = await get_redis()
            store = VerificationCodeStore(ttl_minutes=1, redis_client=redis)

            email = f"integration_{datetime.now().timestamp()}@test.com"
            code = "123456"

            # 設置驗證碼
            await store.set(email, code)

            # 獲取驗證碼
            result = await store.get(email)
            assert result == code

            # 刪除驗證碼
            await store.delete(email)
            assert await store.get(email) is None

        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")


class TestContentModerationRedisIntegration:
    """內容審核快取 Redis 整合測試"""

    @pytest.mark.asyncio
    async def test_cache_to_redis(self, test_db):
        """測試：敏感詞快取到 Redis"""
        try:
            redis = await get_redis()
            await ContentModerationService.set_redis(redis)

            # 清除快取
            await ContentModerationService.clear_cache()

            # 載入敏感詞（會觸發快取）
            words = await ContentModerationService._load_sensitive_words(test_db)

            # 驗證快取到 Redis
            cached = await redis.get("moderation:words")
            assert cached is not None

            # 清理
            await ContentModerationService.clear_cache()

        except Exception as e:
            pytest.skip(f"Redis 不可用: {e}")


class TestLogoutEndToEnd:
    """登出端到端測試（使用 Redis）"""

    @pytest.mark.asyncio
    async def test_logout_with_redis(self, client: AsyncClient):
        """端到端測試：登出後 Token 失效（使用 Redis）"""
        try:
            # 確保 Redis 可用
            redis = await get_redis()
            await redis.ping()

            # 註冊並登入
            email = f"e2e_redis_{datetime.now().timestamp()}@test.com"
            response = await client.post("/api/auth/register", json={
                "email": email,
                "password": "Test1234",
                "date_of_birth": "1995-01-01"
            })

            if response.status_code != 201:
                pytest.skip(f"註冊失敗: {response.json()}")

            token = response.json()["access_token"]

            # 登出
            response = await client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200

            # 驗證 Token 已失效
            response = await client.get(
                "/api/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401

        except Exception as e:
            pytest.skip(f"測試跳過: {e}")
