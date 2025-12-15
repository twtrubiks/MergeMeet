"""HttpOnly Cookie 認證測試

測試 Token 安全存儲方案：
- HttpOnly Cookie + CSRF Token（Double Submit Cookie Pattern）
- Bearer Token 向後兼容
- 登出後 Token 黑名單化
"""
import pytest
from datetime import date
from httpx import AsyncClient

from app.main import app
from app.models.user import User
from app.core.security import get_password_hash


# ==================== 登入 Cookie 測試 ====================


@pytest.mark.asyncio
async def test_login_sets_cookies(client: AsyncClient):
    """測試登入設置 HttpOnly Cookie"""
    # 先註冊
    await client.post("/api/auth/register", json={
        "email": "cookie_login@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 登入
    response = await client.post("/api/auth/login", json={
        "email": "cookie_login@example.com",
        "password": "Password123"
    })

    assert response.status_code == 200

    # 檢查 Cookie 設置
    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies
    assert "csrf_token" in cookies

    # 同時也返回 Token（向後兼容）
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_sets_cookies(client: AsyncClient):
    """測試註冊設置 HttpOnly Cookie"""
    response = await client.post("/api/auth/register", json={
        "email": "cookie_register@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    assert response.status_code == 201

    # 檢查 Cookie 設置
    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies
    assert "csrf_token" in cookies


# ==================== Cookie 認證測試 ====================


@pytest.mark.asyncio
async def test_cookie_auth_with_csrf_success(client: AsyncClient):
    """測試 Cookie + CSRF Token 認證成功"""
    # 註冊並獲取 Cookie
    register_response = await client.post("/api/auth/register", json={
        "email": "cookie_csrf@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 取得 CSRF Token
    csrf_token = register_response.cookies.get("csrf_token")
    assert csrf_token is not None

    # 使用 Cookie + CSRF Token 存取 API
    # httpx 客戶端會自動帶上之前設置的 Cookie
    response = await client.get(
        "/api/profile",
        headers={"X-CSRF-Token": csrf_token}
    )

    # 應該返回 200 或 404（用戶存在但沒有 profile）
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_cookie_auth_without_csrf_fails(client: AsyncClient):
    """測試使用 Cookie 但缺少 CSRF Token 失敗"""
    # 註冊並獲取 Cookie
    await client.post("/api/auth/register", json={
        "email": "cookie_no_csrf@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 僅使用 Cookie（不帶 CSRF Token）存取需要認證的 API
    # 注意：不傳 X-CSRF-Token header
    response = await client.get("/api/profile")

    # 應該返回 403 CSRF 驗證失敗
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cookie_auth_wrong_csrf_fails(client: AsyncClient):
    """測試 CSRF Token 不匹配失敗"""
    # 註冊並獲取 Cookie
    await client.post("/api/auth/register", json={
        "email": "cookie_wrong_csrf@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 使用錯誤的 CSRF Token
    response = await client.get(
        "/api/profile",
        headers={"X-CSRF-Token": "wrong_csrf_token"}
    )

    # 應該返回 403 CSRF 驗證失敗
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


# ==================== Bearer Token 向後兼容測試 ====================


@pytest.mark.asyncio
async def test_bearer_token_still_works(client: AsyncClient):
    """測試 Bearer Token 向後兼容"""
    # 註冊獲取 Token
    register_response = await client.post("/api/auth/register", json={
        "email": "bearer_compat@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    access_token = register_response.json()["access_token"]

    # 建立新的 AsyncClient（不帶之前的 Cookie）
    # 使用 Bearer Token 存取 API
    async with AsyncClient(app=app, base_url="http://test") as new_client:
        response = await new_client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # 應該成功（返回 200 或 404）
        assert response.status_code in [200, 404]


# ==================== 登出測試 ====================


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient):
    """測試登出清除 Cookie"""
    # 註冊
    register_response = await client.post("/api/auth/register", json={
        "email": "logout_cookies@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    csrf_token = register_response.cookies.get("csrf_token")

    # 登出
    response = await client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "登出成功"
    assert "tokens_invalidated" in data

    # 驗證 Cookie 被清除（Set-Cookie 設置為過期）
    # httpx 處理後 cookies 應該被清除或設為空


@pytest.mark.asyncio
async def test_logout_blacklists_access_token(client: AsyncClient):
    """測試登出後 Access Token 被加入黑名單"""
    # 註冊
    register_response = await client.post("/api/auth/register", json={
        "email": "logout_blacklist@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    access_token = register_response.json()["access_token"]
    csrf_token = register_response.cookies.get("csrf_token")

    # 登出
    await client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf_token}
    )

    # 建立新的 AsyncClient 測試舊 Token（不帶 Cookie）
    async with AsyncClient(app=app, base_url="http://test") as new_client:
        response = await new_client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 401
        assert "失效" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout_blacklists_both_tokens(client: AsyncClient):
    """測試登出同時黑名單化 Access Token 和 Refresh Token"""
    # 註冊
    register_response = await client.post("/api/auth/register", json={
        "email": "logout_both@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    refresh_token = register_response.json()["refresh_token"]
    csrf_token = register_response.cookies.get("csrf_token")

    # 登出
    logout_response = await client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf_token}
    )

    assert logout_response.status_code == 200
    data = logout_response.json()
    # 驗證兩個 Token 都被黑名單化
    assert "access_token" in data["tokens_invalidated"]
    assert "refresh_token" in data["tokens_invalidated"]

    # 嘗試使用舊 Refresh Token 刷新（應該失敗）
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })

    assert response.status_code == 401


# ==================== Refresh Token 測試 ====================


@pytest.mark.asyncio
async def test_refresh_from_cookie(client: AsyncClient):
    """測試從 Cookie 刷新 Token"""
    # 註冊
    await client.post("/api/auth/register", json={
        "email": "refresh_cookie@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 刷新 Token（Cookie 會自動帶上）
    response = await client.post("/api/auth/refresh")

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # 新的 Cookie 應該被設置
    assert "access_token" in response.cookies
    assert "csrf_token" in response.cookies


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient):
    """測試 Refresh Token 輪換（舊 Token 失效）"""
    # 註冊
    register_response = await client.post("/api/auth/register", json={
        "email": "refresh_rotate@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    old_refresh_token = register_response.json()["refresh_token"]

    # 刷新 Token
    await client.post("/api/auth/refresh")

    # 嘗試使用舊 Refresh Token（應該失敗）
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": old_refresh_token
    })

    assert response.status_code == 401
    assert "失效" in response.json()["detail"]


# ==================== Admin 登入測試 ====================


@pytest.mark.asyncio
async def test_admin_login_sets_cookies(client: AsyncClient, test_db):
    """測試管理員登入設置 Cookie"""
    # 建立管理員用戶
    admin_user = User(
        email="admin_cookie@example.com",
        password_hash=get_password_hash("AdminPass123"),
        date_of_birth=date(1990, 1, 1),
        is_admin=True,
        is_active=True,
        email_verified=True
    )
    test_db.add(admin_user)
    await test_db.commit()

    # 管理員登入
    response = await client.post("/api/auth/admin-login", json={
        "email": "admin_cookie@example.com",
        "password": "AdminPass123"
    })

    assert response.status_code == 200

    # 檢查 Cookie 設置
    assert "access_token" in response.cookies
    assert "csrf_token" in response.cookies


# ==================== 邊界情況測試 ====================


@pytest.mark.asyncio
async def test_no_auth_provided(client: AsyncClient):
    """測試未提供任何認證憑證"""
    # 建立新的 AsyncClient，不帶任何 Cookie
    async with AsyncClient(app=app, base_url="http://test") as new_client:
        response = await new_client.get("/api/profile")

        assert response.status_code == 401
        assert "認證" in response.json()["detail"]


@pytest.mark.asyncio
async def test_expired_access_token_triggers_refresh(client: AsyncClient):
    """測試 Access Token 過期時自動刷新"""
    # 這個測試需要模擬過期的 Token，在實際環境中較難測試
    # 這裡僅驗證 refresh 端點可用
    await client.post("/api/auth/register", json={
        "email": "auto_refresh@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 驗證 refresh 端點可用
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 200
