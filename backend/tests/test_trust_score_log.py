"""信任分數審計日誌測試

驗證：
- adjust_score 同交易寫入 trust_score_logs
- 日誌欄位正確（action / adjustment / new_score / reason）
- 管理員查詢端點（最新在前、404、權限）
"""

import uuid
from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.trust_score_log import TrustScoreLog
from app.models.user import User
from app.services.trust_score import TrustScoreService

# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession) -> User:
    """創建測試用戶"""
    user = User(
        id=uuid.uuid4(),
        email="trust_log_test@example.com",
        password_hash="dummy_hash",
        date_of_birth=date(1995, 1, 1),
        is_active=True,
        trust_score=50,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, test_db: AsyncSession) -> dict:
    """創建管理員並取得認證 Headers"""
    admin = User(
        id=uuid.uuid4(),
        email="trust_log_admin@example.com",
        password_hash=get_password_hash("Admin123"),
        date_of_birth=date(1990, 1, 1),
        is_active=True,
        is_admin=True,
    )
    test_db.add(admin)
    await test_db.commit()

    response = await client.post(
        "/api/auth/admin-login",
        json={"email": "trust_log_admin@example.com", "password": "Admin123"},
    )
    token = response.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


async def get_logs(db: AsyncSession, user_id: uuid.UUID) -> list[TrustScoreLog]:
    """取得用戶的所有日誌（時間升冪）"""
    result = await db.execute(
        select(TrustScoreLog)
        .where(TrustScoreLog.user_id == user_id)
        .order_by(TrustScoreLog.created_at)
    )
    return list(result.scalars().all())


# ==================== 服務層：日誌寫入 ====================


@pytest.mark.asyncio
class TestAdjustScoreWritesLog:
    """adjust_score 寫入審計日誌"""

    async def test_adjustment_creates_log_entry(self, test_db: AsyncSession, test_user: User):
        """調整分數時寫入一筆日誌，欄位正確"""
        await TrustScoreService.adjust_score(
            test_db, test_user.id, "report_confirmed", reason="舉報 xxx 成立"
        )

        logs = await get_logs(test_db, test_user.id)
        assert len(logs) == 1
        assert logs[0].action == "report_confirmed"
        assert logs[0].adjustment == -10
        assert logs[0].new_score == 40
        assert logs[0].reason == "舉報 xxx 成立"
        assert logs[0].created_at is not None

    async def test_reason_is_optional(self, test_db: AsyncSession, test_user: User):
        """未提供 reason 時日誌仍寫入"""
        await TrustScoreService.adjust_score(test_db, test_user.id, "email_verified")

        logs = await get_logs(test_db, test_user.id)
        assert len(logs) == 1
        assert logs[0].reason is None

    async def test_multiple_adjustments_create_multiple_logs(
        self, test_db: AsyncSession, test_user: User
    ):
        """多次調整產生多筆日誌，new_score 反映累積結果"""
        await TrustScoreService.adjust_score(test_db, test_user.id, "email_verified")  # 50 -> 55
        await TrustScoreService.adjust_score(test_db, test_user.id, "blocked")  # 55 -> 53
        await TrustScoreService.adjust_score(test_db, test_user.id, "match_created")  # 53 -> 55

        logs = await get_logs(test_db, test_user.id)
        assert [(log.action, log.new_score) for log in logs] == [
            ("email_verified", 55),
            ("blocked", 53),
            ("match_created", 55),
        ]

    async def test_capped_adjustment_logs_actual_new_score(
        self, test_db: AsyncSession, test_user: User
    ):
        """觸及分數邊界時，adjustment 記名目值、new_score 記實際值"""
        test_user.trust_score = 98
        await test_db.commit()

        await TrustScoreService.adjust_score(test_db, test_user.id, "email_verified")  # +5 封頂

        logs = await get_logs(test_db, test_user.id)
        assert logs[0].adjustment == 5
        assert logs[0].new_score == 100

    async def test_unknown_action_writes_no_log(self, test_db: AsyncSession, test_user: User):
        """未知行為類型不寫日誌"""
        with pytest.raises(ValueError):
            await TrustScoreService.adjust_score(test_db, test_user.id, "invalid_action")

        logs = await get_logs(test_db, test_user.id)
        assert logs == []


# ==================== 管理員查詢端點 ====================


@pytest.mark.asyncio
class TestTrustLogsEndpoint:
    """GET /api/admin/users/{user_id}/trust-logs"""

    async def test_returns_logs_newest_first(
        self, client: AsyncClient, test_db: AsyncSession, test_user: User, admin_headers: dict
    ):
        """回傳日誌最新在前"""
        await TrustScoreService.adjust_score(test_db, test_user.id, "email_verified")
        await TrustScoreService.adjust_score(
            test_db, test_user.id, "report_confirmed", reason="舉報 abc 成立"
        )

        response = await client.get(
            f"/api/admin/users/{test_user.id}/trust-logs", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["action"] == "report_confirmed"
        assert data[0]["adjustment"] == -10
        assert data[0]["reason"] == "舉報 abc 成立"
        assert data[1]["action"] == "email_verified"

    async def test_user_without_logs_returns_empty_list(
        self, client: AsyncClient, test_user: User, admin_headers: dict
    ):
        """無日誌的用戶回傳空列表"""
        response = await client.get(
            f"/api/admin/users/{test_user.id}/trust-logs", headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_unknown_user_returns_404(self, client: AsyncClient, admin_headers: dict):
        """用戶不存在回傳 404"""
        response = await client.get(
            f"/api/admin/users/{uuid.uuid4()}/trust-logs", headers=admin_headers
        )

        assert response.status_code == 404

    async def test_requires_admin(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """一般用戶無法存取"""
        response = await client.get(
            f"/api/admin/users/{test_user.id}/trust-logs", headers=auth_headers
        )

        assert response.status_code == 403
