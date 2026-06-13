"""刪除帳號功能測試

涵蓋：
- POST /api/auth/delete-account（軟刪除 + 30 天寬限期）
- 登入復原流程（寬限期內自動復原、逾期拒絕）
- 軟刪除期間從配對列表、對話列表隱身、無法被喜歡
- 到期清理任務 purge_expired_accounts
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.profile import Profile
from app.models.user import User
from app.services.account_cleanup import purge_expired_accounts
from app.services.file_storage import file_storage


async def _get_user_by_email(db: AsyncSession, email: str) -> User:
    """以 email 取得用戶"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one()


@pytest.fixture
async def matched_users(client: AsyncClient, auth_user_pair: dict, test_db: AsyncSession):
    """創建已配對的測試用戶（Alice & Bob，含可見且完整的檔案）"""
    alice_token = auth_user_pair["alice"]["token"]
    bob_token = auth_user_pair["bob"]["token"]

    for token, name, gender in [(alice_token, "Alice", "female"), (bob_token, "Bob", "male")]:
        resp = await client.post(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "display_name": name,
                "gender": gender,
                "bio": "測試用戶",
                "location": {
                    "latitude": 25.0330,
                    "longitude": 121.5654,
                    "location_name": "台北市信義區",
                },
            },
        )
        assert resp.status_code == 201

    alice = await _get_user_by_email(test_db, auth_user_pair["alice"]["email"])
    bob = await _get_user_by_email(test_db, auth_user_pair["bob"]["email"])

    # 設為完整且可見（like 驗證需要 is_complete）
    result = await test_db.execute(select(Profile).where(Profile.user_id.in_([alice.id, bob.id])))
    for profile in result.scalars().all():
        profile.is_complete = True
        profile.is_visible = True

    # 直接創建配對（確保 user1_id < user2_id）
    user1_id, user2_id = (alice.id, bob.id) if alice.id < bob.id else (bob.id, alice.id)
    match = Match(user1_id=user1_id, user2_id=user2_id, status="ACTIVE")
    test_db.add(match)
    await test_db.commit()
    await test_db.refresh(match)

    return {
        "alice": {
            "token": alice_token,
            "user_id": str(alice.id),
            "email": auth_user_pair["alice"]["email"],
            "headers": {"Authorization": f"Bearer {alice_token}"},
        },
        "bob": {
            "token": bob_token,
            "user_id": str(bob.id),
            "email": auth_user_pair["bob"]["email"],
            "headers": {"Authorization": f"Bearer {bob_token}"},
        },
        "match_id": str(match.id),
    }


# ==================== 刪除端點 ====================


@pytest.mark.asyncio
async def test_delete_account_success(
    client: AsyncClient, auth_user: dict, sample_user_data: dict, test_db: AsyncSession
):
    """正確密碼刪除成功，標記 deleted_at 並停用帳號"""
    response = await client.post(
        "/api/auth/delete-account",
        headers=auth_user["headers"],
        json={"password": sample_user_data["password"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted_at" in data
    assert "restore_deadline" in data

    user = await _get_user_by_email(test_db, auth_user["email"])
    await test_db.refresh(user)
    assert user.deleted_at is not None
    assert user.is_active is False


@pytest.mark.asyncio
async def test_delete_account_wrong_password(client: AsyncClient, auth_user: dict):
    """密碼錯誤回傳 400"""
    response = await client.post(
        "/api/auth/delete-account",
        headers=auth_user["headers"],
        json={"password": "WrongPassword123"},
    )

    assert response.status_code == 400
    assert "密碼錯誤" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_account_unauthenticated(client: AsyncClient):
    """未認證回傳 401"""
    response = await client.post("/api/auth/delete-account", json={"password": "Test1234!"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_invalidates_tokens(
    client: AsyncClient, auth_user: dict, sample_user_data: dict
):
    """刪除後舊 Token 無法再使用"""
    response = await client.post(
        "/api/auth/delete-account",
        headers=auth_user["headers"],
        json={"password": sample_user_data["password"]},
    )
    assert response.status_code == 200

    # 舊 Token 被黑名單化（401）或被 is_active 擋下（403）
    response = await client.get("/api/profile", headers=auth_user["headers"])
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_account_already_deleted(
    client: AsyncClient, auth_user: dict, sample_user_data: dict, test_db: AsyncSession
):
    """重複刪除回傳 400"""
    user = await _get_user_by_email(test_db, auth_user["email"])
    # 保留 is_active=True 以通過認證依賴，模擬不一致狀態下的防禦檢查
    user.deleted_at = datetime.now(UTC)
    await test_db.commit()

    response = await client.post(
        "/api/auth/delete-account",
        headers=auth_user["headers"],
        json={"password": sample_user_data["password"]},
    )

    assert response.status_code == 400
    assert "刪除程序" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_cannot_delete_account(
    client: AsyncClient, auth_user: dict, sample_user_data: dict, test_db: AsyncSession
):
    """管理員帳號無法自行刪除"""
    user = await _get_user_by_email(test_db, auth_user["email"])
    user.is_admin = True
    await test_db.commit()

    response = await client.post(
        "/api/auth/delete-account",
        headers=auth_user["headers"],
        json={"password": sample_user_data["password"]},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_account_email_sent(
    client: AsyncClient, auth_user: dict, sample_user_data: dict
):
    """刪除時發送通知 Email；發送失敗不影響刪除流程"""
    with patch(
        "app.api.auth.EmailService.send_account_deleted_email",
        new_callable=AsyncMock,
        return_value=False,  # 模擬發送失敗
    ) as mock_send:
        response = await client.post(
            "/api/auth/delete-account",
            headers=auth_user["headers"],
            json={"password": sample_user_data["password"]},
        )

    assert response.status_code == 200
    mock_send.assert_awaited_once()
    assert mock_send.await_args.kwargs["to_email"] == auth_user["email"]


# ==================== 登入復原 ====================


@pytest.mark.asyncio
async def test_login_within_grace_restores(
    client: AsyncClient, auth_user: dict, sample_user_data: dict, test_db: AsyncSession
):
    """寬限期內重新登入自動復原帳號"""
    response = await client.post(
        "/api/auth/delete-account",
        headers=auth_user["headers"],
        json={"password": sample_user_data["password"]},
    )
    assert response.status_code == 200

    # 等待跨秒，避免新 Token 的 iat/exp 與被黑名單的舊 Token 完全相同（payload 相同則 JWT 相同）
    await asyncio.sleep(1.1)

    # 重新登入
    response = await client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": sample_user_data["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account_restored"] is True

    user = await _get_user_by_email(test_db, auth_user["email"])
    await test_db.refresh(user)
    assert user.deleted_at is None
    assert user.is_active is True

    # 新 Token 可正常使用（404 表示未建檔案但認證通過）
    client.cookies.clear()  # 清除 login 設置的 Cookie，改用 Bearer 模式
    response = await client.get(
        "/api/profile", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_login_normal_not_restored(
    client: AsyncClient, auth_user: dict, sample_user_data: dict
):
    """一般登入 account_restored 為 False"""
    response = await client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": sample_user_data["password"]},
    )

    assert response.status_code == 200
    assert response.json()["account_restored"] is False


@pytest.mark.asyncio
async def test_login_after_grace_rejected(
    client: AsyncClient, auth_user: dict, sample_user_data: dict, test_db: AsyncSession
):
    """寬限期過後登入被拒絕"""
    user = await _get_user_by_email(test_db, auth_user["email"])
    user.deleted_at = datetime.now(UTC) - timedelta(days=31)
    user.is_active = False
    await test_db.commit()

    response = await client.post(
        "/api/auth/login",
        json={"email": auth_user["email"], "password": sample_user_data["password"]},
    )

    assert response.status_code == 403
    assert "無法復原" in response.json()["detail"]


# ==================== 軟刪除期間隱身 ====================


async def _soft_delete_user(db: AsyncSession, email: str) -> None:
    """直接在 DB 標記軟刪除（模擬已完成刪除請求的狀態）"""
    user = await _get_user_by_email(db, email)
    user.deleted_at = datetime.now(UTC)
    user.is_active = False
    await db.commit()


@pytest.mark.asyncio
async def test_deleted_user_hidden_from_matches(
    client: AsyncClient, matched_users: dict, test_db: AsyncSession
):
    """已刪除用戶從配對列表消失"""
    # 刪除前：Alice 可見與 Bob 的配對
    response = await client.get("/api/discovery/matches", headers=matched_users["alice"]["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 1

    await _soft_delete_user(test_db, matched_users["bob"]["email"])

    response = await client.get("/api/discovery/matches", headers=matched_users["alice"]["headers"])
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_deleted_user_hidden_from_conversations(
    client: AsyncClient, matched_users: dict, test_db: AsyncSession
):
    """已刪除用戶從對話列表消失"""
    response = await client.get(
        "/api/messages/conversations", headers=matched_users["alice"]["headers"]
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    await _soft_delete_user(test_db, matched_users["bob"]["email"])

    response = await client.get(
        "/api/messages/conversations", headers=matched_users["alice"]["headers"]
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_cannot_like_deleted_user(
    client: AsyncClient, matched_users: dict, test_db: AsyncSession
):
    """無法對已刪除用戶送出喜歡"""
    bob_id = matched_users["bob"]["user_id"]

    await _soft_delete_user(test_db, matched_users["bob"]["email"])

    response = await client.post(
        f"/api/discovery/like/{bob_id}", headers=matched_users["alice"]["headers"]
    )
    assert response.status_code == 404


# ==================== 到期清理任務 ====================


@pytest.mark.asyncio
async def test_purge_expired_accounts(
    client: AsyncClient, matched_users: dict, test_db: AsyncSession
):
    """寬限期過後永久刪除帳號（含 CASCADE、照片目錄、聊天圖片目錄）"""
    bob_id = matched_users["bob"]["user_id"]
    match_id = matched_users["match_id"]

    # 建立假照片與聊天圖片檔案
    photo_dir = file_storage.photos_dir / bob_id
    photo_dir.mkdir(parents=True, exist_ok=True)
    (photo_dir / "test.jpg").write_bytes(b"fake-image")

    chat_dir = file_storage.chat_dir / match_id
    chat_dir.mkdir(parents=True, exist_ok=True)
    (chat_dir / "chat.jpg").write_bytes(b"fake-image")

    # 標記為 31 天前刪除
    bob = await _get_user_by_email(test_db, matched_users["bob"]["email"])
    bob_uuid = bob.id
    bob.deleted_at = datetime.now(UTC) - timedelta(days=31)
    bob.is_active = False
    await test_db.commit()

    purged = await purge_expired_accounts(test_db)
    assert purged == 1

    # User row 與關聯資料（CASCADE）消失
    result = await test_db.execute(select(User).where(User.id == bob_uuid))
    assert result.scalar_one_or_none() is None
    result = await test_db.execute(select(Profile).where(Profile.user_id == bob_uuid))
    assert result.scalar_one_or_none() is None
    result = await test_db.execute(select(Match).where(Match.id == match_id))
    assert result.scalar_one_or_none() is None

    # 檔案目錄消失
    assert not photo_dir.exists()
    assert not chat_dir.exists()

    # Alice 不受影響
    result = await test_db.execute(
        select(User).where(User.email == matched_users["alice"]["email"])
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_purge_keeps_grace_period_accounts(
    client: AsyncClient, auth_user: dict, test_db: AsyncSession
):
    """寬限期內的帳號不會被清除"""
    user = await _get_user_by_email(test_db, auth_user["email"])
    user.deleted_at = datetime.now(UTC) - timedelta(days=5)
    user.is_active = False
    await test_db.commit()

    purged = await purge_expired_accounts(test_db)
    assert purged == 0

    result = await test_db.execute(select(User).where(User.email == auth_user["email"]))
    assert result.scalar_one_or_none() is not None
