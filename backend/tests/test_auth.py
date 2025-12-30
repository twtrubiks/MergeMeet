"""認證 API 測試"""
import asyncio
import pytest
import secrets
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, timedelta, timezone

from app.main import app
from app.models.user import User
from app.core.security import get_password_hash
from app.api.auth import verification_codes, generate_verification_code
from app.services.token_invalidator import TokenInvalidator
from app.services.redis_client import get_redis


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

    # 重新發送驗證碼（使用 JSON body）
    response = await client.post(
        "/api/auth/resend-verification",
        json={"email": "resend@example.com"}
    )

    assert response.status_code == 200
    # 訊息格式已更新為防止用戶枚舉的模糊訊息
    assert "已註冊" in response.json()["message"] or "已發送" in response.json()["message"]


@pytest.mark.asyncio
async def test_resend_verification_invalid_email_format(client: AsyncClient):
    """測試重新發送驗證碼 - 無效 email 格式被拒絕"""
    response = await client.post(
        "/api/auth/resend-verification",
        json={"email": "not-a-valid-email"}
    )

    # Pydantic EmailStr 驗證應返回 422
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_resend_verification_nonexistent_email_no_leak(client: AsyncClient):
    """測試重新發送驗證碼 - 不存在的 email 不洩露資訊（防止用戶枚舉）"""
    response = await client.post(
        "/api/auth/resend-verification",
        json={"email": "nonexistent_user_12345@example.com"}
    )

    # 應返回 200 而非 404（防止攻擊者探測 email 是否存在）
    assert response.status_code == 200
    assert "已註冊" in response.json()["message"]


@pytest.mark.asyncio
async def test_resend_verification_already_verified_no_leak(client: AsyncClient, db_session: AsyncSession):
    """測試重新發送驗證碼 - 已驗證的 email 不洩露資訊"""
    # 註冊用戶
    await client.post("/api/auth/register", json={
        "email": "verified_user@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 手動設置為已驗證
    result = await db_session.execute(
        select(User).where(User.email == "verified_user@example.com")
    )
    user = result.scalar_one()
    user.email_verified = True
    await db_session.commit()

    # 重新發送驗證碼
    response = await client.post(
        "/api/auth/resend-verification",
        json={"email": "verified_user@example.com"}
    )

    # 應返回 200 而非 400（防止攻擊者探測 email 驗證狀態）
    assert response.status_code == 200
    assert "已註冊" in response.json()["message"]


@pytest.mark.asyncio
async def test_verify_email_nonexistent_user_no_leak(client: AsyncClient):
    """測試驗證 Email - 不存在的用戶不洩露資訊（防止用戶枚舉）"""
    response = await client.post("/api/auth/verify-email", json={
        "email": "nonexistent_verify_12345@example.com",
        "verification_code": "123456"
    })

    # 應返回 400 而非 404，且訊息與驗證碼錯誤相同
    assert response.status_code == 400
    assert "驗證碼" in response.json()["detail"]


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


# ==================== 密碼重置功能測試 ====================


@pytest.mark.asyncio
async def test_forgot_password(client: AsyncClient):
    """測試忘記密碼 - 發送重置郵件"""
    # 先註冊
    await client.post("/api/auth/register", json={
        "email": "forgot@example.com",
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 請求密碼重置
    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": "forgot@example.com"}
    )

    assert response.status_code == 200
    # 不透露 email 是否存在
    assert "如果" in response.json()["message"]


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email(client: AsyncClient):
    """測試忘記密碼 - 不存在的 email 也返回相同訊息（防止枚舉）"""
    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": "nonexistent@example.com"}
    )

    # 應該返回成功（防止 email 枚舉）
    assert response.status_code == 200
    assert "如果" in response.json()["message"]


@pytest.mark.asyncio
async def test_verify_reset_token_returns_masked_email(client: AsyncClient, db_session: AsyncSession):
    """測試驗證重置 Token 返回遮罩 email"""
    # 直接創建用戶並設置重置 token
    reset_token = secrets.token_urlsafe(32)
    user = User(
        email="resettest@example.com",
        password_hash=get_password_hash("Password123"),
        date_of_birth=date(1995, 1, 1),
        password_reset_token=reset_token,
        password_reset_expires=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db_session.add(user)
    await db_session.commit()

    # 驗證 token
    response = await client.get(
        "/api/auth/verify-reset-token",
        params={"token": reset_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    # 確認 email 已被遮罩（不是完整 email）
    assert data["email"] is not None
    assert "***" in data["email"]
    assert data["email"] != "resettest@example.com"


@pytest.mark.asyncio
async def test_verify_reset_token_invalid(client: AsyncClient):
    """測試驗證無效的重置 Token"""
    response = await client.get(
        "/api/auth/verify-reset-token",
        params={"token": "invalid_token_here"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["email"] is None


# ==================== 驗證碼生成測試 ====================


@pytest.mark.asyncio
async def test_verification_code_format():
    """測試驗證碼格式（6 位數字）"""
    for _ in range(10):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()


# ==================== 驗證碼暴力破解防護測試 ====================


@pytest.mark.asyncio
async def test_verify_email_rate_limit(client: AsyncClient):
    """測試驗證碼嘗試次數限制（5 次失敗後鎖定）"""
    # 使用唯一 email 避免與其他測試衝突
    unique_email = f"ratelimit_{uuid.uuid4().hex[:8]}@example.com"

    # 先註冊
    await client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })

    # 嘗試 5 次錯誤驗證碼
    for i in range(5):
        response = await client.post("/api/auth/verify-email", json={
            "email": unique_email,
            "verification_code": "000000"
        })
        if i < 4:
            assert response.status_code == 400, f"Attempt {i+1}: {response.json()}"
            assert "剩餘" in response.json()["detail"]
        else:
            # 第 5 次應該觸發鎖定
            assert response.status_code == 429, f"Attempt {i+1}: {response.json()}"
            assert "嘗試次數過多" in response.json()["detail"]

    # 被鎖定後再次嘗試應該返回 429
    response = await client.post("/api/auth/verify-email", json={
        "email": unique_email,
        "verification_code": "123456"
    })
    assert response.status_code == 429


# ==================== 密碼重置 Token 失效測試 ====================


@pytest.mark.asyncio
async def test_reset_password_invalidates_tokens(client: AsyncClient, db_session: AsyncSession):
    """測試密碼重置後舊 Token 失效"""
    # 使用唯一 email 避免與其他測試衝突
    unique_email = f"resetinvalidate_{uuid.uuid4().hex[:8]}@example.com"

    # 初始化 TokenInvalidator（測試環境）
    try:
        redis_conn = await get_redis()
        TokenInvalidator.set_redis(redis_conn)
    except Exception:
        pytest.skip("Redis not available")

    # 註冊並取得 Token
    register_response = await client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password123",
        "date_of_birth": "1995-01-01"
    })
    assert register_response.status_code == 201
    old_token = register_response.json()["access_token"]

    # 設置密碼重置 Token
    reset_token = secrets.token_urlsafe(32)
    result = await db_session.execute(
        select(User).where(User.email == unique_email)
    )
    user = result.scalar_one()
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await db_session.commit()

    # 等待一秒確保 Token iat 早於失效時間戳（秒級精度）
    await asyncio.sleep(1)

    # 執行密碼重置
    reset_response = await client.post("/api/auth/reset-password", json={
        "token": reset_token,
        "new_password": "NewPassword456"
    })
    assert reset_response.status_code == 200

    # 使用舊 Token 嘗試登出應該失敗（Token 已失效）
    async with AsyncClient(app=app, base_url="http://test") as new_client:
        logout_response = await new_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        assert logout_response.status_code == 401, (
            f"Expected 401, got {logout_response.status_code}: {logout_response.json()}"
        )
        assert "密碼已變更" in logout_response.json()["detail"]
