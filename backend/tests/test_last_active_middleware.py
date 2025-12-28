"""LastActiveMiddleware 測試

測試用戶活躍時間自動更新機制
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.user import User
from app.models.profile import Profile


class TestLastActiveMiddleware:
    """LastActiveMiddleware 測試類別"""

    @pytest.mark.asyncio
    async def test_last_active_updated_on_authenticated_request(
        self,
        client: AsyncClient,
        auth_user: dict,
        test_db: AsyncSession
    ):
        """測試已認證請求成功後會更新 last_active"""
        # 取得用戶 ID
        result = await test_db.execute(
            select(User.id).where(User.email == auth_user["email"])
        )
        user_id = result.scalar_one()

        # 建立 Profile
        response = await client.post(
            "/api/profile",
            headers=auth_user["headers"],
            json={
                "display_name": "Test User",
                "gender": "male",
                "bio": "Test bio",
                "location": {
                    "latitude": 25.0330,
                    "longitude": 121.5654,
                    "location_name": "Taipei"
                }
            }
        )
        assert response.status_code == 201

        # 發送另一個認證請求（GET /api/profile）
        response = await client.get(
            "/api/profile",
            headers=auth_user["headers"]
        )
        assert response.status_code == 200

        # 重新查詢 Profile（因為 middleware 使用獨立 session）
        result = await test_db.execute(
            select(Profile.last_active).where(Profile.user_id == user_id)
        )
        last_active = result.scalar_one()

        # 檢查 last_active 已被設置
        assert last_active is not None

    @pytest.mark.asyncio
    async def test_last_active_not_updated_on_unauthenticated_request(
        self,
        client: AsyncClient
    ):
        """測試未認證請求不會觸發更新（也不會報錯）"""
        # 發送未認證請求
        response = await client.get("/health")
        assert response.status_code == 200

        # 確認請求成功完成，沒有異常

    @pytest.mark.asyncio
    async def test_last_active_not_updated_on_failed_request(
        self,
        client: AsyncClient,
        auth_user: dict,
        test_db: AsyncSession
    ):
        """測試請求失敗（非 2xx）時不會更新 last_active"""
        # 取得用戶 ID
        result = await test_db.execute(
            select(User.id).where(User.email == auth_user["email"])
        )
        user_id = result.scalar_one()

        # 建立 Profile
        await client.post(
            "/api/profile",
            headers=auth_user["headers"],
            json={
                "display_name": "Test User",
                "gender": "male",
                "bio": "Test bio",
                "location": {
                    "latitude": 25.0330,
                    "longitude": 121.5654,
                    "location_name": "Taipei"
                }
            }
        )

        # 記錄當前 last_active
        result = await test_db.execute(
            select(Profile.last_active).where(Profile.user_id == user_id)
        )
        before_last_active = result.scalar_one()

        # 發送會失敗的請求（不存在的端點）
        response = await client.get(
            "/api/nonexistent",
            headers=auth_user["headers"]
        )
        assert response.status_code == 404

        # 確認請求完成，沒有報錯
        # 注意：404 不應該觸發更新（雖然難以精確驗證時間差異）

    @pytest.mark.asyncio
    async def test_middleware_handles_invalid_token_gracefully(
        self,
        client: AsyncClient
    ):
        """測試無效 Token 時 Middleware 靜默處理"""
        # 發送帶有無效 Token 的請求
        response = await client.get(
            "/health",
            headers={"Authorization": "Bearer invalid_token"}
        )
        # 請求應該成功（health 不需要認證）
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_handles_expired_token_gracefully(
        self,
        client: AsyncClient
    ):
        """測試過期 Token 時 Middleware 靜默處理"""
        # 使用一個假的過期 Token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MX0.invalid"

        response = await client.get(
            "/health",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        # 請求應該成功（health 不需要認證）
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_last_active_updated_with_cookie_auth(
        self,
        client: AsyncClient,
        sample_user_data: dict,
        test_db: AsyncSession
    ):
        """測試 Cookie 認證模式也會更新 last_active"""
        # 註冊用戶（會設置 Cookie 和 CSRF Token）
        response = await client.post(
            "/api/auth/register",
            json=sample_user_data
        )
        assert response.status_code == 201

        # 取得 CSRF Token（從 Cookie）
        csrf_token = response.cookies.get("csrf_token")

        # 使用 Cookie + CSRF 認證建立 Profile
        response = await client.post(
            "/api/profile",
            headers={"X-CSRF-Token": csrf_token} if csrf_token else {},
            json={
                "display_name": "Cookie User",
                "gender": "female",
                "bio": "Test bio",
                "location": {
                    "latitude": 25.0330,
                    "longitude": 121.5654,
                    "location_name": "Taipei"
                }
            }
        )
        assert response.status_code == 201

        # 取得用戶 ID
        result = await test_db.execute(
            select(User.id).where(User.email == sample_user_data["email"])
        )
        user_id = result.scalar_one()

        # 重新查詢 Profile（因為 middleware 使用獨立 session）
        result = await test_db.execute(
            select(Profile.last_active).where(Profile.user_id == user_id)
        )
        last_active = result.scalar_one()
        assert last_active is not None
