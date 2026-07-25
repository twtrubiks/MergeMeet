"""全域 IP 速率限制測試

驗證 slowapi 整合：
- 全域限制（application-level，所有端點共用 per-IP 計數）
- 認證端點獨立的更嚴格限制（登入/註冊 10 次/5 分鐘）
- /health 豁免
- 429 回應格式與 headers

Note:
    conftest 的 client fixture 預設停用速率限制，
    此處透過 rate_limited_client fixture 啟用並於前後重置計數。
"""

import pytest_asyncio
from httpx import AsyncClient

from app.core.config import settings
from app.core.rate_limit import limiter

# 解析設定中的全域上限（"60/minute" -> 60），測試與設定保持同步
GLOBAL_LIMIT = int(settings.RATE_LIMIT_GLOBAL.split("/")[0])
AUTH_LIMIT = int(settings.RATE_LIMIT_AUTH.split("/")[0])


@pytest_asyncio.fixture
async def rate_limited_client(client: AsyncClient):
    """啟用速率限制的測試 Client（前後重置計數，避免測試間與跨次執行污染）"""
    limiter.reset()
    limiter.enabled = True
    yield client
    limiter.enabled = False
    limiter.reset()


class TestGlobalRateLimit:
    """全域 per-IP 限制（所有端點共用計數）"""

    async def test_response_contains_rate_limit_headers(self, rate_limited_client: AsyncClient):
        """正常請求回應帶有 X-RateLimit-* headers"""
        response = await rate_limited_client.get("/")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == str(GLOBAL_LIMIT)
        assert int(response.headers["X-RateLimit-Remaining"]) == GLOBAL_LIMIT - 1

    async def test_exceeding_global_limit_returns_429(self, rate_limited_client: AsyncClient):
        """超過全域限制回傳 429，且計數跨端點共用"""
        for _ in range(GLOBAL_LIMIT - 1):
            response = await rate_limited_client.get("/")
            assert response.status_code == 200

        # 第 60 次改打 /openapi.json：不同端點共用同一組計數，仍可成功
        response = await rate_limited_client.get("/openapi.json")
        assert response.status_code == 200

        # 第 61 次：超限，無論打哪個端點都被拒絕
        response = await rate_limited_client.get("/")
        assert response.status_code == 429
        assert response.json() == {"detail": "請求過於頻繁，請稍後再試"}
        assert "Retry-After" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    async def test_health_check_is_exempt(self, rate_limited_client: AsyncClient):
        """/health 豁免：即使全域計數已耗盡仍可存取（供監控輪詢）"""
        for _ in range(GLOBAL_LIMIT):
            await rate_limited_client.get("/")

        # 全域計數已滿，一般端點被拒絕
        response = await rate_limited_client.get("/")
        assert response.status_code == 429

        # /health 不受影響
        response = await rate_limited_client.get("/health")
        assert response.status_code == 200


class TestAuthRateLimit:
    """認證端點獨立限制（10 次/5 分鐘 per IP，與 email-based LoginLimiter 互補）"""

    async def test_login_rate_limit(self, rate_limited_client: AsyncClient):
        """登入超過 IP 限制回傳 429（使用不同 email 避開 email-based 鎖定）"""
        for i in range(AUTH_LIMIT):
            response = await rate_limited_client.post(
                "/api/auth/login",
                json={"email": f"rl-test-{i}@example.com", "password": "Wrong1234!"},
            )
            # 未超限前：帳號不存在 -> 401（而非 429）
            assert response.status_code == 401

        response = await rate_limited_client.post(
            "/api/auth/login",
            json={"email": "rl-test-last@example.com", "password": "Wrong1234!"},
        )
        assert response.status_code == 429
        assert response.json() == {"detail": "請求過於頻繁，請稍後再試"}

    async def test_register_rate_limit(self, rate_limited_client: AsyncClient):
        """註冊超過 IP 限制回傳 429（使用未滿 18 歲資料，不實際建立帳號）"""
        payload = {
            "email": "minor@example.com",
            "password": "Test1234!",
            "date_of_birth": "2015-01-01",
        }
        for _ in range(AUTH_LIMIT):
            response = await rate_limited_client.post("/api/auth/register", json=payload)
            assert response.status_code == 400  # 年齡驗證失敗，但已計入限制

        response = await rate_limited_client.post("/api/auth/register", json=payload)
        assert response.status_code == 429

    async def test_auth_limit_independent_from_global(self, rate_limited_client: AsyncClient):
        """認證端點由裝飾器獨立計數，不消耗全域額度"""
        response = await rate_limited_client.post(
            "/api/auth/login",
            json={"email": "independent@example.com", "password": "Wrong1234!"},
        )
        assert response.status_code == 401

        # 全域計數未被登入請求消耗
        response = await rate_limited_client.get("/")
        assert int(response.headers["X-RateLimit-Remaining"]) == GLOBAL_LIMIT - 1


class TestRateLimitDisabled:
    """停用時不限制（conftest 預設行為，其餘測試依賴此特性）"""

    async def test_disabled_limiter_allows_unlimited_requests(self, client: AsyncClient):
        for _ in range(GLOBAL_LIMIT + 5):
            response = await client.get("/")
            assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers
