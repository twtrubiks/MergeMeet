"""認證 API 測試"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.main import app
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


# ==================== 密碼修改功能測試 ====================


@pytest.fixture
async def user_for_password_change(client: AsyncClient):
    """建立測試用戶（用於密碼修改測試）"""
    response = await client.post("/api/auth/register", json={
        "email": "pwdchange@example.com",
        "password": "OldPassword123",
        "date_of_birth": "1995-01-01"
    })
    assert response.status_code == 201
    return {
        "token": response.json()["access_token"],
        "csrf_token": response.cookies.get("csrf_token"),  # 新增：CSRF Token
        "email": "pwdchange@example.com",
        "password": "OldPassword123"
    }


# === 成功案例 ===


@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient, user_for_password_change: dict):
    """測試密碼修改成功"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "NewPassword456"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "成功" in data["message"]
    assert data["tokens_invalidated"] is True


@pytest.mark.asyncio
async def test_change_password_token_invalidated(client: AsyncClient, user_for_password_change: dict):
    """測試修改密碼後原 Token 失效"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    # 修改密碼
    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "NewPassword456"
        }
    )
    assert response.status_code == 200

    # 使用舊 Token 存取 API 應失敗（建立新 client 避免 Cookie 影響）
    async with AsyncClient(app=app, base_url="http://test") as new_client:
        response = await new_client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_can_login_with_new(client: AsyncClient, user_for_password_change: dict):
    """測試修改密碼後可用新密碼登入"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]
    email = user_for_password_change["email"]

    # 修改密碼
    await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "NewPassword456"
        }
    )

    # 用新密碼登入
    response = await client.post("/api/auth/login", json={
        "email": email,
        "password": "NewPassword456"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_change_password_cannot_login_with_old(client: AsyncClient, user_for_password_change: dict):
    """測試修改密碼後舊密碼無法登入"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]
    email = user_for_password_change["email"]

    # 修改密碼
    await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "NewPassword456"
        }
    )

    # 用舊密碼登入應失敗
    response = await client.post("/api/auth/login", json={
        "email": email,
        "password": "OldPassword123"
    })
    assert response.status_code == 401


# === 當前密碼驗證 ===


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, user_for_password_change: dict):
    """測試當前密碼錯誤"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "WrongPassword123",
            "new_password": "NewPassword456"
        }
    )

    assert response.status_code == 400
    assert "當前密碼錯誤" in response.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_empty_current(client: AsyncClient, user_for_password_change: dict):
    """測試當前密碼為空"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "",
            "new_password": "NewPassword456"
        }
    )

    assert response.status_code == 422


# === 新密碼驗證 ===


@pytest.mark.asyncio
async def test_change_password_same_as_current(client: AsyncClient, user_for_password_change: dict):
    """測試新密碼與舊密碼相同"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "OldPassword123"
        }
    )

    assert response.status_code == 400
    assert "相同" in response.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_too_short(client: AsyncClient, user_for_password_change: dict):
    """測試新密碼少於 8 字元"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "Short1"
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_no_uppercase(client: AsyncClient, user_for_password_change: dict):
    """測試新密碼無大寫字母"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "newpassword123"
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_no_lowercase(client: AsyncClient, user_for_password_change: dict):
    """測試新密碼無小寫字母"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "NEWPASSWORD123"
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_no_digit(client: AsyncClient, user_for_password_change: dict):
    """測試新密碼無數字"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "NewPasswordOnly"
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_weak(client: AsyncClient, user_for_password_change: dict):
    """測試新密碼為弱密碼"""
    token = user_for_password_change["token"]
    csrf_token = user_for_password_change["csrf_token"]

    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf_token
        },
        json={
            "current_password": "OldPassword123",
            "new_password": "Password"  # 常見弱密碼
        }
    )

    assert response.status_code == 422


# === 認證 ===


@pytest.mark.asyncio
async def test_change_password_unauthorized(client: AsyncClient):
    """測試未帶 Token 修改密碼"""
    # 使用新的 client 避免之前測試留下的 Cookie 影響
    async with AsyncClient(app=app, base_url="http://test") as new_client:
        response = await new_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123",
                "new_password": "NewPassword456"
            }
        )

        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_change_password_invalid_token(client: AsyncClient):
    """測試無效 Token 修改密碼"""
    # 使用新的 client 避免之前測試留下的 Cookie 影響
    async with AsyncClient(app=app, base_url="http://test") as new_client:
        response = await new_client.post(
            "/api/auth/change-password",
            headers={"Authorization": "Bearer invalid_token_here"},
            json={
                "current_password": "OldPassword123",
                "new_password": "NewPassword456"
            }
        )

        assert response.status_code == 401
