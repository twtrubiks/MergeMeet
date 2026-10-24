"""Redis 整合測試

需要實際 Redis 服務運行。
使用 pytest 標記：@pytest.mark.integration

執行方式：
    pytest tests/test_redis_integration.py -v -m integration

注意：這些測試需要 Redis 服務運行在 localhost:6379（連不上時整個測試 skip）
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
import redis.asyncio as aioredis
from httpx import AsyncClient

from app.core.config import settings
from app.services.content_moderation import ContentModerationService
from app.services.token_blacklist import TokenBlacklist
from app.services.verification_code import VerificationCodeStore

# 標記所有測試為整合測試
pytestmark = pytest.mark.integration


@pytest.fixture
async def real_redis():
    """每個測試獨立的 Redis 連線

    不共用全域連線池：池中連線綁定建立時的 event loop，跨測試重用會
    Event loop is closed。只有連不上 Redis 時才 skip；斷言失敗必須照常失敗
    （原本整段包在 except Exception: skip 內，斷言失敗也被當成「Redis 不可用」跳過）。
    """
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await client.ping()
    except (aioredis.ConnectionError, OSError) as e:
        await client.aclose()
        pytest.skip(f"Redis 不可用: {e}")
    yield client
    await client.aclose()


class TestRedisConnection:
    """Redis 連線測試"""

    @pytest.mark.asyncio
    async def test_redis_ping(self, real_redis):
        """測試 Redis 連線 - ping"""
        assert await real_redis.ping() is True


class TestTokenBlacklistRedisIntegration:
    """Token 黑名單 Redis 整合測試"""

    @pytest.mark.asyncio
    async def test_add_and_check_real_redis(self, real_redis):
        """測試：使用真實 Redis 的 Token 黑名單操作"""
        blacklist = TokenBlacklist(redis_client=real_redis)

        token = f"integration_test_token_{datetime.now().timestamp()}"
        expires_at = datetime.now(UTC) + timedelta(minutes=1)

        # 加入黑名單
        await blacklist.add(token, expires_at)

        # 驗證在黑名單中（且確實寫進 Redis，而非回退到內存）
        assert await blacklist.is_blacklisted(token) is True
        assert blacklist.is_using_redis() is True

        # 清理
        assert await blacklist.remove(token) is True
        assert await blacklist.is_blacklisted(token) is False

    @pytest.mark.asyncio
    async def test_redis_ttl_works(self, real_redis):
        """測試：Redis TTL 自動過期"""
        blacklist = TokenBlacklist(redis_client=real_redis)

        token = f"ttl_test_token_{datetime.now().timestamp()}"
        # 設置 2 秒後過期
        expires_at = datetime.now(UTC) + timedelta(seconds=2)

        await blacklist.add(token, expires_at)

        # 立即檢查應該在黑名單中
        assert await blacklist.is_blacklisted(token) is True

        # 等待過期
        await asyncio.sleep(3)

        # 過期後應該不在黑名單中
        assert await blacklist.is_blacklisted(token) is False


class TestVerificationCodeRedisIntegration:
    """驗證碼存儲 Redis 整合測試"""

    @pytest.mark.asyncio
    async def test_set_and_get_real_redis(self, real_redis):
        """測試：使用真實 Redis 的驗證碼操作"""
        store = VerificationCodeStore(ttl_minutes=1, redis_client=real_redis)

        email = f"integration_{datetime.now().timestamp()}@test.com"
        code = "123456"

        # 設置驗證碼
        await store.set(email, code)

        # 獲取驗證碼（且確實存在 Redis，TTL 為 1 分鐘）
        assert await store.get(email) == code
        assert 0 < await real_redis.ttl(f"verify:{email}") <= 60

        # 刪除驗證碼
        await store.delete(email)
        assert await store.get(email) is None


class TestContentModerationRedisIntegration:
    """內容審核快取 Redis 整合測試"""

    @pytest.mark.asyncio
    async def test_cache_to_redis(self, test_db, real_redis, monkeypatch):
        """測試：敏感詞快取到 Redis"""
        # 測試後還原 class 層級的 Redis 狀態（否則後續測試會沿用這條已關閉的連線）
        monkeypatch.setattr(ContentModerationService, "_redis", None)
        monkeypatch.setattr(ContentModerationService, "_use_redis", False)
        await ContentModerationService.set_redis(real_redis)

        # 清除快取
        await ContentModerationService.clear_cache()

        # 載入敏感詞（會觸發快取）
        await ContentModerationService._load_sensitive_words(test_db)

        # 驗證快取到 Redis
        assert await real_redis.get("moderation:words") is not None

        # 清理
        await ContentModerationService.clear_cache()


class TestLogoutEndToEnd:
    """登出端到端測試（使用 Redis）"""

    @pytest.mark.asyncio
    async def test_logout_with_redis(self, client: AsyncClient, real_redis):
        """端到端測試：登出後 Token 失效（使用 Redis）"""
        # 註冊並登入
        email = f"e2e_redis_{datetime.now().timestamp()}@test.com"
        response = await client.post(
            "/api/auth/register",
            json={"email": email, "password": "Test1234", "date_of_birth": "1995-01-01"},
        )
        assert response.status_code == 201, response.text

        token = response.json()["access_token"]
        # 清除 Cookie，確保使用 Bearer Token 認證（避免 CSRF 驗證）
        client.cookies.clear()

        # 登出
        response = await client.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # 黑名單確實寫進 Redis
        assert await real_redis.exists(f"blacklist:{TokenBlacklist._hash_token(token)}") == 1

        # 驗證 Token 已失效
        response = await client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
