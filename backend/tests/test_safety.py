"""安全功能測試 - 封鎖與舉報"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.match import Match


@pytest.fixture
async def test_users_for_safety(client: AsyncClient):
    """創建測試用戶（Alice, Bob, Charlie）"""
    # 註冊 Alice
    response_a = await client.post("/api/auth/register", json={
        "email": "alice_safety@example.com",
        "password": "Alice1234",
        "date_of_birth": "1995-06-15"
    })
    assert response_a.status_code == 201
    token_a = response_a.json()["access_token"]

    # 註冊 Bob
    response_b = await client.post("/api/auth/register", json={
        "email": "bob_safety@example.com",
        "password": "Bob12345",
        "date_of_birth": "1990-03-20"
    })
    assert response_b.status_code == 201
    token_b = response_b.json()["access_token"]

    # 註冊 Charlie
    response_c = await client.post("/api/auth/register", json={
        "email": "charlie_safety@example.com",
        "password": "Charlie123",
        "date_of_birth": "1992-08-10"
    })
    assert response_c.status_code == 201
    token_c = response_c.json()["access_token"]

    # 從 token 解析出 user_id（簡化版，實際應該解碼 JWT）
    # 這裡假設我們可以從資料庫查詢
    return {
        "alice": {"token": token_a, "email": "alice_safety@example.com"},
        "bob": {"token": token_b, "email": "bob_safety@example.com"},
        "charlie": {"token": token_c, "email": "charlie_safety@example.com"}
    }


@pytest.mark.asyncio
async def test_block_user_success(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：成功封鎖用戶"""
    # 取得 Bob 的 user_id
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    # Alice 封鎖 Bob
    response = await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["blocked"] is True
    assert data["message"] == "已封鎖用戶"


@pytest.mark.asyncio
async def test_cannot_block_self(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：無法封鎖自己"""
    # 取得 Alice 自己的 user_id
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['alice']['email'])
    )
    alice = result.scalar_one()

    # Alice 嘗試封鎖自己
    response = await client.post(
        f"/api/safety/block/{alice.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "測試"}
    )

    assert response.status_code == 400
    assert "無法封鎖自己" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_block_twice(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：無法重複封鎖同一用戶"""
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    # Alice 第一次封鎖 Bob
    await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"}
    )

    # Alice 第二次嘗試封鎖 Bob
    response = await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "再次封鎖"}
    )

    assert response.status_code == 400
    assert "已經封鎖" in response.json()["detail"]


@pytest.mark.asyncio
async def test_unblock_user_success(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：成功解除封鎖"""
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    # Alice 先封鎖 Bob
    await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"}
    )

    # Alice 解除封鎖 Bob
    response = await client.delete(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["unblocked"] is True
    assert data["message"] == "已解除封鎖"


@pytest.mark.asyncio
async def test_get_blocked_users_list(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：取得封鎖列表"""
    from sqlalchemy import select

    # 取得 Bob 和 Charlie 的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['charlie']['email'])
    )
    charlie = result.scalar_one()

    # Alice 封鎖 Bob 和 Charlie
    await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "原因1"}
    )
    await client.post(
        f"/api/safety/block/{charlie.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "原因2"}
    )

    # 取得封鎖列表
    response = await client.get(
        "/api/safety/blocked",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(u["blocked_user_email"] == test_users_for_safety['bob']['email'] for u in data)
    assert any(u["blocked_user_email"] == test_users_for_safety['charlie']['email'] for u in data)


@pytest.mark.asyncio
async def test_block_cancels_match(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：封鎖自動取消配對"""
    from sqlalchemy import select
    import uuid

    # 取得 Alice 和 Bob 的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['alice']['email'])
    )
    alice = result.scalar_one()

    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    # 手動創建一個配對記錄
    user1_id = min(alice.id, bob.id)
    user2_id = max(alice.id, bob.id)

    match = Match(
        user1_id=user1_id,
        user2_id=user2_id,
        status="ACTIVE"
    )
    test_db.add(match)
    await test_db.commit()

    # Alice 封鎖 Bob
    response = await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["match_cancelled"] is True

    # 驗證配對已取消
    result = await test_db.execute(
        select(Match).where(Match.id == match.id)
    )
    updated_match = result.scalar_one()
    assert updated_match.status == "UNMATCHED"
    assert updated_match.unmatched_by == alice.id


# ==================== 舉報功能測試 ====================

@pytest.mark.asyncio
async def test_report_user_success(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：成功舉報用戶"""
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    # Alice 舉報 Bob
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(bob.id),
            "report_type": "HARASSMENT",
            "reason": "此用戶傳送不當訊息，讓我感到不舒服",
            "evidence": "多次傳送騷擾訊息"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reported_user_id"] == str(bob.id)
    assert data["report_type"] == "HARASSMENT"
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_cannot_report_self(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：無法舉報自己"""
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['alice']['email'])
    )
    alice = result.scalar_one()

    # Alice 嘗試舉報自己
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(alice.id),
            "report_type": "OTHER",
            "reason": "測試用的舉報原因文字"
        }
    )

    assert response.status_code == 400
    assert "無法舉報自己" in response.json()["detail"]


@pytest.mark.asyncio
async def test_report_requires_valid_type(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：舉報類型必須有效"""
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    # Alice 使用無效的舉報類型
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(bob.id),
            "report_type": "INVALID_TYPE",
            "reason": "這是一個測試舉報的原因"
        }
    )

    assert response.status_code == 400
    assert "無效的舉報類型" in response.json()["detail"]


@pytest.mark.asyncio
async def test_report_nonexistent_user(client: AsyncClient, test_users_for_safety: dict):
    """測試：舉報不存在的用戶"""
    import uuid

    # Alice 舉報不存在的用戶
    fake_user_id = str(uuid.uuid4())
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": fake_user_id,
            "report_type": "FAKE",
            "reason": "這是一個測試舉報的原因"
        }
    )

    assert response.status_code == 404
    assert "被舉報用戶不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_my_reports(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：取得我的舉報記錄"""
    from sqlalchemy import select

    # 取得 Bob 和 Charlie 的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()

    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['charlie']['email'])
    )
    charlie = result.scalar_one()

    # Alice 舉報 Bob
    await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(bob.id),
            "report_type": "HARASSMENT",
            "reason": "騷擾行為讓我感到不適"
        }
    )

    # Alice 舉報 Charlie
    await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(charlie.id),
            "report_type": "FAKE",
            "reason": "疑似假帳號，個人資料可疑"
        }
    )

    # 取得舉報記錄
    response = await client.get(
        "/api/safety/reports",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(r["report_type"] == "HARASSMENT" for r in data)
    assert any(r["report_type"] == "FAKE" for r in data)


@pytest.mark.asyncio
async def test_report_increases_warning_count(client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession):
    """測試：舉報會增加被舉報用戶的警告次數"""
    from sqlalchemy import select

    # 取得 Bob 的初始警告次數
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety['bob']['email'])
    )
    bob = result.scalar_one()
    initial_warning_count = bob.warning_count

    # Alice 舉報 Bob
    await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(bob.id),
            "report_type": "INAPPROPRIATE",
            "reason": "不當行為讓我感到不舒服"
        }
    )

    # 刷新並檢查警告次數
    await test_db.refresh(bob)
    assert bob.warning_count == initial_warning_count + 1
