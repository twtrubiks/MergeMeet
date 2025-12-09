"""認證 API 測試"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.models.user import User
from app.api.auth import verification_codes


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """測試註冊成功"""
    response = await client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_underage(client: AsyncClient):
    """測試未滿 18 歲無法註冊"""
    response = await client.post("/api/auth/register", json={
        "email": "young@example.com",
        "password": "Password123",
        "date_of_birth": "2010-01-01"
    })

    assert response.status_code == 400
    assert "18 歲" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """測試重複 Email 無法註冊（使用模糊訊息防止用戶枚舉）"""
    # 第一次註冊
    await client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 第二次註冊同一個 Email
    response = await client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "password": "Password456",
        "date_of_birth": "1996-01-01"
    })

    assert response.status_code == 400
    # 安全考量：不透露 Email 是否已註冊（防止用戶枚舉）
    assert "註冊失敗" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """測試弱密碼無法註冊"""
    # 沒有大寫字母
    response = await client.post("/api/auth/register", json={
        "email": "weak1@example.com",
        "password": "password123",
        "date_of_birth": "1995-01-01"
    })
    assert response.status_code == 422

    # 沒有小寫字母
    response = await client.post("/api/auth/register", json={
        "email": "weak2@example.com",
        "password": "PASSWORD123",
        "date_of_birth": "1995-01-01"
    })
    assert response.status_code == 422

    # 沒有數字
    response = await client.post("/api/auth/register", json={
        "email": "weak3@example.com",
        "password": "PasswordOnly",
        "date_of_birth": "1995-01-01"
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """測試登入成功"""
    # 先註冊
    await client.post("/api/auth/register", json={
        "email": "logintest@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 登入
    response = await client.post("/api/auth/login", json={
        "email": "logintest@example.com",
        "password": "Password123"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """測試密碼錯誤"""
    # 先註冊
    await client.post("/api/auth/register", json={
        "email": "wrongpass@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 使用錯誤密碼登入
    response = await client.post("/api/auth/login", json={
        "email": "wrongpass@example.com",
        "password": "WrongPassword"
    })

    assert response.status_code == 401
    assert "錯誤" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """測試不存在的用戶"""
    response = await client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "Password123"
    })

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """測試刷新 Token"""
    # 先註冊
    register_response = await client.post("/api/auth/register", json={
        "email": "refreshtest@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    refresh_token = register_response.json()["refresh_token"]

    # 刷新 Token
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """測試無效的 Refresh Token"""
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": "invalid_token"
    })

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_email_success(client: AsyncClient):
    """測試 Email 驗證成功"""
    # 先註冊（這會生成驗證碼）
    await client.post("/api/auth/register", json={
        "email": "verify@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 從 auth.py 的 verification_codes 字典中取得驗證碼
    code = await verification_codes.get("verify@example.com")  # ✅ 添加 await

    # 驗證 Email
    response = await client.post("/api/auth/verify-email", json={
        "email": "verify@example.com",
        "verification_code": code
    })

    assert response.status_code == 200
    assert response.json()["verified"] is True


@pytest.mark.asyncio
async def test_verify_email_wrong_code(client: AsyncClient):
    """測試錯誤的驗證碼"""
    # 先註冊
    await client.post("/api/auth/register", json={
        "email": "wrongcode@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 使用錯誤的驗證碼
    response = await client.post("/api/auth/verify-email", json={
        "email": "wrongcode@example.com",
        "verification_code": "000000"
    })

    assert response.status_code == 400
    assert "錯誤" in response.json()["detail"]


@pytest.mark.asyncio
async def test_resend_verification(client: AsyncClient):
    """測試重新發送驗證碼"""
    # 先註冊
    await client.post("/api/auth/register", json={
        "email": "resend@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 重新發送驗證碼
    response = await client.post(
        "/api/auth/resend-verification",
        params={"email": "resend@example.com"}
    )

    assert response.status_code == 200
    assert "重新發送" in response.json()["message"]
