"""安全功能測試 - 封鎖與舉報"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import BlockedUser, Match
from app.models.profile import Profile
from app.models.report import Report
from app.models.user import User


@pytest.fixture
async def test_users_for_safety(auth_user_trio: dict):
    """創建測試用戶（Alice, Bob, Charlie）"""
    return {
        "alice": {
            "token": auth_user_trio["alice"]["token"],
            "email": auth_user_trio["alice"]["email"],
        },
        "bob": {"token": auth_user_trio["bob"]["token"], "email": auth_user_trio["bob"]["email"]},
        "charlie": {
            "token": auth_user_trio["charlie"]["token"],
            "email": auth_user_trio["charlie"]["email"],
        },
    }


@pytest.mark.asyncio
async def test_block_user_success(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：成功封鎖用戶"""
    # 取得 Bob 的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    # Alice 封鎖 Bob
    response = await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["blocked"] is True
    assert data["message"] == "已封鎖用戶"


@pytest.mark.asyncio
async def test_cannot_block_self(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：無法封鎖自己"""
    # 取得 Alice 自己的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["alice"]["email"])
    )
    alice = result.scalar_one()

    # Alice 嘗試封鎖自己
    response = await client.post(
        f"/api/safety/block/{alice.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "測試"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "無法封鎖自己"


@pytest.mark.asyncio
async def test_cannot_block_twice(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：無法重複封鎖同一用戶"""
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    # Alice 第一次封鎖 Bob
    await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"},
    )

    # Alice 第二次嘗試封鎖 Bob
    response = await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "再次封鎖"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "已經封鎖此用戶"


@pytest.mark.asyncio
async def test_unblock_user_success(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：成功解除封鎖"""
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    # Alice 先封鎖 Bob
    await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"},
    )

    # Alice 解除封鎖 Bob
    response = await client.delete(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["unblocked"] is True
    assert data["message"] == "已解除封鎖"


@pytest.mark.asyncio
async def test_get_blocked_users_list(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：取得封鎖列表"""

    # 取得 Bob 和 Charlie 的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["charlie"]["email"])
    )
    charlie = result.scalar_one()

    # Alice 封鎖 Bob 和 Charlie
    await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "原因1"},
    )
    await client.post(
        f"/api/safety/block/{charlie.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "原因2"},
    )

    # 取得封鎖列表
    response = await client.get(
        "/api/safety/blocked",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # 驗證不洩露 email，改為顯示 display_name（測試中未建立 Profile，應為 fallback 值）
    for u in data:
        assert "blocked_user_email" not in u
        assert "blocked_user_display_name" in u


@pytest.mark.asyncio
async def test_block_cancels_match(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：封鎖自動取消配對"""

    # 取得 Alice 和 Bob 的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["alice"]["email"])
    )
    alice = result.scalar_one()

    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    # 手動創建一個配對記錄
    user1_id = min(alice.id, bob.id)
    user2_id = max(alice.id, bob.id)

    match = Match(user1_id=user1_id, user2_id=user2_id, status="ACTIVE")
    test_db.add(match)
    await test_db.commit()

    # Alice 封鎖 Bob
    response = await client.post(
        f"/api/safety/block/{bob.id}",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={"reason": "不當行為"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["match_cancelled"] is True

    # 驗證配對已取消
    result = await test_db.execute(select(Match).where(Match.id == match.id))
    updated_match = result.scalar_one()
    assert updated_match.status == "UNMATCHED"
    assert updated_match.unmatched_by == alice.id


# ==================== 舉報功能測試 ====================


@pytest.mark.asyncio
async def test_report_user_success(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：成功舉報用戶"""
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
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
            "evidence": "多次傳送騷擾訊息",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reported_user_id"] == str(bob.id)
    assert data["report_type"] == "HARASSMENT"
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_cannot_report_self(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：無法舉報自己"""
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["alice"]["email"])
    )
    alice = result.scalar_one()

    # Alice 嘗試舉報自己
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(alice.id),
            "report_type": "OTHER",
            "reason": "測試用的舉報原因文字",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "無法舉報自己"


@pytest.mark.asyncio
async def test_report_requires_valid_type(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：舉報類型必須有效"""
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    # Alice 使用無效的舉報類型
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(bob.id),
            "report_type": "INVALID_TYPE",
            "reason": "這是一個測試舉報的原因",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "無效的舉報類型。有效類型：INAPPROPRIATE, HARASSMENT, FAKE, SCAM, OTHER"
    )


@pytest.mark.asyncio
async def test_report_nonexistent_user(client: AsyncClient, test_users_for_safety: dict):
    """測試：舉報不存在的用戶"""

    # Alice 舉報不存在的用戶
    fake_user_id = str(uuid.uuid4())
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": fake_user_id,
            "report_type": "FAKE",
            "reason": "這是一個測試舉報的原因",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "被舉報用戶不存在"


@pytest.mark.asyncio
async def test_get_my_reports(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：取得我的舉報記錄"""

    # 取得 Bob 和 Charlie 的 user_id
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["charlie"]["email"])
    )
    charlie = result.scalar_one()

    # Alice 舉報 Bob
    await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(bob.id),
            "report_type": "HARASSMENT",
            "reason": "騷擾行為讓我感到不適",
        },
    )

    # Alice 舉報 Charlie
    await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(charlie.id),
            "report_type": "FAKE",
            "reason": "疑似假帳號，個人資料可疑",
        },
    )

    # 取得舉報記錄
    response = await client.get(
        "/api/safety/reports",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(r["report_type"] == "HARASSMENT" for r in data)
    assert any(r["report_type"] == "FAKE" for r in data)


@pytest.mark.asyncio
async def test_report_does_not_change_score_or_warning(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：提交舉報不會立即扣分或增加警告次數（需管理員確認後才執行）"""

    # 取得 Bob 的初始狀態
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()
    initial_warning_count = bob.warning_count
    initial_trust_score = bob.trust_score

    # Alice 舉報 Bob
    response = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json={
            "reported_user_id": str(bob.id),
            "report_type": "INAPPROPRIATE",
            "reason": "不當行為讓我感到不舒服",
        },
    )
    assert response.status_code == 201

    # 刷新並檢查：分數和警告次數都不應改變
    await test_db.refresh(bob)
    assert bob.warning_count == initial_warning_count
    assert bob.trust_score == initial_trust_score


@pytest.mark.asyncio
async def test_duplicate_report_rejected(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """測試：對同一用戶重複提交舉報（PENDING 狀態）應被拒絕"""

    # 取得 Bob
    result = await test_db.execute(
        select(User).where(User.email == test_users_for_safety["bob"]["email"])
    )
    bob = result.scalar_one()

    report_data = {
        "reported_user_id": str(bob.id),
        "report_type": "HARASSMENT",
        "reason": "騷擾行為讓我感到不舒服的體驗",
    }

    # 第一次舉報應成功
    response1 = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json=report_data,
    )
    assert response1.status_code == 201

    # 第二次舉報同一人應被拒絕
    response2 = await client.post(
        "/api/safety/report",
        headers={"Authorization": f"Bearer {test_users_for_safety['alice']['token']}"},
        json=report_data,
    )
    assert response2.status_code == 400
    assert response2.json()["detail"] == "您已對該用戶提交過舉報，目前正在處理中"


# ==================== 封鎖／舉報的歸屬與邊界 ====================


async def _users(db: AsyncSession, users: dict) -> dict[str, User]:
    result = await db.execute(select(User))
    by_email = {user.email: user for user in result.scalars().all()}
    return {name: by_email[info["email"]] for name, info in users.items()}


def _headers(users: dict, name: str) -> dict:
    return {"Authorization": f"Bearer {users[name]['token']}"}


@pytest.mark.asyncio
async def test_block_nonexistent_user(client: AsyncClient, test_users_for_safety: dict):
    response = await client.post(
        f"/api/safety/block/{uuid.uuid4()}",
        headers=_headers(test_users_for_safety, "alice"),
        json={},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "用戶不存在"


@pytest.mark.asyncio
async def test_block_not_prevented_by_others_block(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """別人封鎖過 Bob，不影響 Alice 封鎖 Bob"""
    users = await _users(test_db, test_users_for_safety)
    test_db.add(BlockedUser(blocker_id=users["charlie"].id, blocked_id=users["bob"].id))
    await test_db.commit()

    response = await client.post(
        f"/api/safety/block/{users['bob'].id}",
        headers=_headers(test_users_for_safety, "alice"),
        json={},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_block_cancels_match_whichever_side_blocks(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """配對中 user1 封鎖 user2、或 user2 封鎖 user1，都會取消配對並記錄時間與執行者"""
    users = await _users(test_db, test_users_for_safety)
    names = {user.id: name for name, user in users.items()}
    pairs = [
        sorted([users["alice"].id, users["bob"].id]),
        sorted([users["alice"].id, users["charlie"].id]),
    ]
    matches = [Match(user1_id=low, user2_id=high, status="ACTIVE") for low, high in pairs]
    # 每個人都另有與 id 最小、最大者的配對：條件只比對一邊時會找到這些無關的配對
    lowest = User(
        id=uuid.UUID(int=1),
        email="low@example.com",
        password_hash="x",
        date_of_birth=date(1995, 1, 1),
    )
    highest = User(
        id=uuid.UUID(int=2**128 - 1),
        email="high@example.com",
        password_hash="x",
        date_of_birth=date(1995, 1, 1),
    )
    test_db.add_all([lowest, highest])
    await test_db.commit()
    unrelated = [
        Match(user1_id=lowest.id, user2_id=user.id, status="ACTIVE") for user in users.values()
    ] + [Match(user1_id=user.id, user2_id=highest.id, status="ACTIVE") for user in users.values()]
    test_db.add_all([*matches, *unrelated])
    await test_db.commit()

    # 第一組由 user1（id 較小者）封鎖，第二組由 user2 封鎖
    for (blocker, blocked), match in zip(
        [(pairs[0][0], pairs[0][1]), (pairs[1][1], pairs[1][0])], matches, strict=True
    ):
        response = await client.post(
            f"/api/safety/block/{blocked}",
            headers=_headers(test_users_for_safety, names[blocker]),
            json={},
        )
        assert response.status_code == 201
        assert response.json()["match_cancelled"] is True

        await test_db.refresh(match)
        assert (match.status, match.unmatched_by) == ("UNMATCHED", blocker)
        assert match.unmatched_at is not None

    for match in unrelated:
        await test_db.refresh(match)
    assert {match.status for match in unrelated} == {"ACTIVE"}


@pytest.mark.asyncio
async def test_block_leaves_already_unmatched_match_untouched(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """已解除的配對不會再被「取消」一次（不覆寫原本的解除者）"""
    users = await _users(test_db, test_users_for_safety)
    low, high = sorted([users["alice"].id, users["bob"].id])
    match = Match(user1_id=low, user2_id=high, status="UNMATCHED", unmatched_by=users["bob"].id)
    test_db.add(match)
    await test_db.commit()

    response = await client.post(
        f"/api/safety/block/{users['bob'].id}",
        headers=_headers(test_users_for_safety, "alice"),
        json={},
    )

    assert response.json()["match_cancelled"] is False
    await test_db.refresh(match)
    assert match.unmatched_by == users["bob"].id


@pytest.mark.asyncio
async def test_blocked_list_newest_first_with_names_and_reasons(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """封鎖列表：最新的在前；有檔案顯示名稱、沒有檔案顯示「未知用戶」；保留封鎖原因"""
    users = await _users(test_db, test_users_for_safety)
    test_db.add(Profile(user_id=users["bob"].id, display_name="Bob 的名字"))
    await test_db.commit()
    alice = _headers(test_users_for_safety, "alice")

    await client.post(
        f"/api/safety/block/{users['bob'].id}", headers=alice, json={"reason": "騷擾"}
    )
    await client.post(f"/api/safety/block/{users['charlie'].id}", headers=alice, json={})
    response = await client.get("/api/safety/blocked", headers=alice)

    assert response.status_code == 200
    blocks = (await test_db.execute(select(BlockedUser))).scalars().all()
    block_ids = {block.blocked_id: str(block.id) for block in blocks}
    assert [
        {key: item[key] for key in ("id", "blocked_user_id", "blocked_user_display_name", "reason")}
        for item in response.json()
    ] == [
        {
            "id": block_ids[users["charlie"].id],
            "blocked_user_id": str(users["charlie"].id),
            "blocked_user_display_name": "未知用戶",
            "reason": None,
        },
        {
            "id": block_ids[users["bob"].id],
            "blocked_user_id": str(users["bob"].id),
            "blocked_user_display_name": "Bob 的名字",
            "reason": "騷擾",
        },
    ]


@pytest.mark.asyncio
async def test_unblock_only_removes_own_block_of_that_user(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    """只能解除自己對該用戶的封鎖：不能解除別人的封鎖，也不會動到自己對其他人的封鎖"""
    users = await _users(test_db, test_users_for_safety)
    test_db.add_all(
        [
            BlockedUser(blocker_id=users["charlie"].id, blocked_id=users["bob"].id),
            BlockedUser(blocker_id=users["alice"].id, blocked_id=users["charlie"].id),
        ]
    )
    await test_db.commit()
    alice = _headers(test_users_for_safety, "alice")

    response = await client.delete(f"/api/safety/block/{users['bob'].id}", headers=alice)
    assert response.status_code == 404
    assert response.json()["detail"] == "未封鎖此用戶"

    test_db.add(BlockedUser(blocker_id=users["alice"].id, blocked_id=users["bob"].id))
    await test_db.commit()
    response = await client.delete(f"/api/safety/block/{users['bob'].id}", headers=alice)
    assert response.status_code == 200

    remaining = (await test_db.execute(select(BlockedUser))).scalars().all()
    assert {(b.blocker_id, b.blocked_id) for b in remaining} == {
        (users["charlie"].id, users["bob"].id),
        (users["alice"].id, users["charlie"].id),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("report_type", ["INAPPROPRIATE", "HARASSMENT", "FAKE", "SCAM", "OTHER"])
async def test_report_accepts_every_valid_type(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession, report_type: str
):
    users = await _users(test_db, test_users_for_safety)

    response = await client.post(
        "/api/safety/report",
        headers=_headers(test_users_for_safety, "alice"),
        json={
            "reported_user_id": str(users["bob"].id),
            "report_type": report_type,
            "reason": "這是一段至少十個字的舉報原因",
            "evidence": "截圖說明",
        },
    )

    assert response.status_code == 201
    [report] = (await test_db.execute(select(Report))).scalars().all()
    assert response.json()["id"] == str(report.id)
    assert (report.report_type, report.evidence, report.status) == (
        report_type,
        "截圖說明",
        "PENDING",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_reporter", "existing_status", "expected"),
    [
        ("alice", "UNDER_REVIEW", 400),  # 處理中的舉報仍算重複
        ("alice", "APPROVED", 201),  # 先前的舉報已審結，可再次舉報
        ("alice", "REJECTED", 201),
        ("charlie", "PENDING", 201),  # 別人的舉報不影響自己舉報
    ],
)
async def test_duplicate_report_only_counts_own_open_reports(
    client: AsyncClient,
    test_users_for_safety: dict,
    test_db: AsyncSession,
    existing_reporter: str,
    existing_status: str,
    expected: int,
):
    users = await _users(test_db, test_users_for_safety)
    test_db.add(
        Report(
            reporter_id=users[existing_reporter].id,
            reported_user_id=users["bob"].id,
            report_type="FAKE",
            reason="先前提交的舉報原因",
            status=existing_status,
        )
    )
    await test_db.commit()

    response = await client.post(
        "/api/safety/report",
        headers=_headers(test_users_for_safety, "alice"),
        json={
            "reported_user_id": str(users["bob"].id),
            "report_type": "HARASSMENT",
            "reason": "這是一段至少十個字的舉報原因",
        },
    )

    assert response.status_code == expected


@pytest.mark.asyncio
async def test_my_reports_newest_first_and_only_mine(
    client: AsyncClient, test_users_for_safety: dict, test_db: AsyncSession
):
    users = await _users(test_db, test_users_for_safety)
    alice = _headers(test_users_for_safety, "alice")
    for target in ("bob", "charlie"):
        await client.post(
            "/api/safety/report",
            headers=alice,
            json={
                "reported_user_id": str(users[target].id),
                "report_type": "OTHER",
                "reason": "這是一段至少十個字的舉報原因",
            },
        )
    await client.post(
        "/api/safety/report",
        headers=_headers(test_users_for_safety, "charlie"),
        json={
            "reported_user_id": str(users["bob"].id),
            "report_type": "OTHER",
            "reason": "這是一段至少十個字的舉報原因",
        },
    )

    response = await client.get("/api/safety/reports", headers=alice)

    reports = (
        (await test_db.execute(select(Report).where(Report.reporter_id == users["alice"].id)))
        .scalars()
        .all()
    )
    report_ids = {report.reported_user_id: str(report.id) for report in reports}
    assert [(r["id"], r["reported_user_id"]) for r in response.json()] == [
        (report_ids[users["charlie"].id], str(users["charlie"].id)),
        (report_ids[users["bob"].id], str(users["bob"].id)),
    ]
