"""信任分數自動恢復測試

驗證：
- 每日衰減恢復：低於預設分（50）的活躍用戶 +1，封頂於 50
- 排除軟刪除與停權用戶
- Redis 日期鎖：當日重複執行不重複加分
- 舉報駁回補償：+5（上限 50、不降分、不重複發放）
- 所有恢復寫入審計日誌
"""

import uuid
from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.report import Report
from app.models.trust_score_log import TrustScoreLog
from app.models.user import User
from app.services.redis_client import redis_client
from app.services.trust_score import TrustScoreService
from app.services.trust_score_recovery import (
    apply_daily_recovery,
    run_daily_recovery_once,
)

# ==================== Fixtures ====================


def make_user(email: str, trust_score: int, **kwargs) -> User:
    kwargs.setdefault("is_active", True)
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash="dummy_hash",
        date_of_birth=date(1995, 1, 1),
        trust_score=trust_score,
        **kwargs,
    )


@pytest_asyncio.fixture
async def recovery_lock_cleanup(client: AsyncClient):
    """清除當日的恢復日期鎖（測試前後），避免跨測試/跨次執行污染

    依賴 client fixture：確保全域 Redis 連線池已由 conftest 在當前測試
    事件循環初始化，避免自行 close/重建連線池導致跨 loop 連線錯誤。
    """
    redis_conn = await redis_client.get_connection()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    lock_key = f"trust:daily_recovery:{today}"
    await redis_conn.delete(lock_key)
    yield
    await redis_conn.delete(lock_key)


async def get_scores(db: AsyncSession, users: list[User]) -> dict[str, int]:
    """取得各用戶當前分數（email -> score）"""
    result = await db.execute(
        select(User.email, User.trust_score).where(User.id.in_([u.id for u in users]))
    )
    return dict(result.all())


# ==================== 每日衰減恢復 ====================


@pytest.mark.asyncio
class TestDailyRecovery:
    """apply_daily_recovery：低於預設分的活躍用戶每日 +1"""

    async def test_only_users_below_default_recover(self, test_db: AsyncSession):
        """低於 50 的用戶 +1；50 以上不變"""
        users = [
            make_user("low30@example.com", 30),
            make_user("low49@example.com", 49),
            make_user("default50@example.com", 50),
            make_user("high80@example.com", 80),
        ]
        test_db.add_all(users)
        await test_db.commit()

        recovered = await apply_daily_recovery(test_db)

        assert recovered == 2
        scores = await get_scores(test_db, users)
        assert scores["low30@example.com"] == 31
        assert scores["low49@example.com"] == 50  # 封頂於預設分
        assert scores["default50@example.com"] == 50
        assert scores["high80@example.com"] == 80

    async def test_excludes_deleted_and_inactive_users(self, test_db: AsyncSession):
        """軟刪除與停權用戶不恢復"""
        users = [
            make_user("active@example.com", 30),
            make_user("deleted@example.com", 30, deleted_at=datetime.now(UTC)),
            make_user("banned@example.com", 30, is_active=False),
        ]
        test_db.add_all(users)
        await test_db.commit()

        recovered = await apply_daily_recovery(test_db)

        assert recovered == 1
        scores = await get_scores(test_db, users)
        assert scores["active@example.com"] == 31
        assert scores["deleted@example.com"] == 30
        assert scores["banned@example.com"] == 30

    async def test_recovery_writes_audit_logs(self, test_db: AsyncSession):
        """每筆恢復寫入審計日誌"""
        user = make_user("audit@example.com", 40)
        test_db.add(user)
        await test_db.commit()

        await apply_daily_recovery(test_db)

        result = await test_db.execute(
            select(TrustScoreLog).where(TrustScoreLog.user_id == user.id)
        )
        logs = list(result.scalars().all())
        assert len(logs) == 1
        assert logs[0].action == "daily_recovery"
        assert logs[0].adjustment == 1
        assert logs[0].new_score == 41
        assert logs[0].reason == "每日自動恢復"

    async def test_no_eligible_users_is_noop(self, test_db: AsyncSession):
        """無符合條件用戶時不動作"""
        test_db.add(make_user("fine@example.com", 75))
        await test_db.commit()

        assert await apply_daily_recovery(test_db) == 0


@pytest.mark.asyncio
class TestDailyRecoveryLock:
    """run_daily_recovery_once：Redis 日期鎖防止當日重複執行"""

    async def test_runs_only_once_per_day(self, test_db: AsyncSession, recovery_lock_cleanup):
        user = make_user("once@example.com", 30)
        test_db.add(user)
        await test_db.commit()

        first = await run_daily_recovery_once(test_db)
        second = await run_daily_recovery_once(test_db)

        assert first == 1
        assert second == 0  # 當日已執行，不重複加分

        scores = await get_scores(test_db, [user])
        assert scores["once@example.com"] == 31


# ==================== 舉報駁回補償 ====================


@pytest.mark.asyncio
class TestReportRejectedCompensation:
    """report_rejected：+5、上限 50、不降分"""

    async def test_compensation_capped_at_default_score(self, test_db: AsyncSession):
        """40 -> 45；48 -> 50（封頂）；60 -> 60（不降分）"""
        cases = [
            (make_user("c40@example.com", 40), 45),
            (make_user("c48@example.com", 48), 50),
            (make_user("c60@example.com", 60), 60),
        ]
        test_db.add_all([user for user, _ in cases])
        await test_db.commit()

        for user, expected in cases:
            new_score = await TrustScoreService.adjust_score(test_db, user.id, "report_rejected")
            assert new_score == expected, user.email

    async def test_compensation_writes_audit_log(self, test_db: AsyncSession):
        """補償寫入審計日誌（記名目 +5 與實際 new_score）"""
        user = make_user("c_log@example.com", 60)
        test_db.add(user)
        await test_db.commit()

        await TrustScoreService.adjust_score(
            test_db, user.id, "report_rejected", reason="舉報 xxx 駁回補償"
        )

        result = await test_db.execute(
            select(TrustScoreLog).where(TrustScoreLog.user_id == user.id)
        )
        log = result.scalar_one()
        assert log.adjustment == 5
        assert log.new_score == 60  # 不降分也不超過原分數
        assert log.reason == "舉報 xxx 駁回補償"


@pytest.mark.asyncio
class TestReviewReportRejected:
    """POST /api/admin/reports/{id}/review 駁回時觸發補償"""

    @pytest_asyncio.fixture
    async def setup(self, client: AsyncClient, test_db: AsyncSession) -> dict:
        """建立管理員、被舉報用戶（40 分）與 PENDING 舉報"""
        admin = User(
            id=uuid.uuid4(),
            email="recovery_admin@example.com",
            password_hash=get_password_hash("Admin123"),
            date_of_birth=date(1990, 1, 1),
            is_active=True,
            is_admin=True,
        )
        reporter = make_user("reporter@example.com", 50)
        reported = make_user("reported@example.com", 40)
        test_db.add_all([admin, reporter, reported])
        await test_db.commit()  # 先寫入用戶，Report 的 FK 才有效

        report = Report(
            id=uuid.uuid4(),
            reporter_id=reporter.id,
            reported_user_id=reported.id,
            report_type="SPAM",
            reason="測試舉報",
        )
        test_db.add(report)
        await test_db.commit()

        response = await client.post(
            "/api/auth/admin-login",
            json={"email": "recovery_admin@example.com", "password": "Admin123"},
        )
        token = response.json()["access_token"]
        client.cookies.clear()

        return {
            "headers": {"Authorization": f"Bearer {token}"},
            "report": report,
            "reported": reported,
        }

    async def test_rejected_report_compensates_reported_user(
        self, client: AsyncClient, test_db: AsyncSession, setup: dict
    ):
        """駁回舉報後被舉報用戶 +5"""
        response = await client.post(
            f"/api/admin/reports/{setup['report'].id}/review",
            json={"status": "REJECTED", "admin_notes": "查無不當行為"},
            headers=setup["headers"],
        )

        assert response.status_code == 200
        scores = await get_scores(test_db, [setup["reported"]])
        assert scores["reported@example.com"] == 45

    async def test_re_rejecting_does_not_compensate_twice(
        self, client: AsyncClient, test_db: AsyncSession, setup: dict
    ):
        """重複駁回同一舉報不重複補償"""
        for _ in range(2):
            response = await client.post(
                f"/api/admin/reports/{setup['report'].id}/review",
                json={"status": "REJECTED"},
                headers=setup["headers"],
            )
            assert response.status_code == 200

        scores = await get_scores(test_db, [setup["reported"]])
        assert scores["reported@example.com"] == 45


@pytest.mark.asyncio
class TestReviewReportApproved:
    """POST /api/admin/reports/{id}/review 成立時扣分（與駁回補償對稱的防重複）"""

    @pytest_asyncio.fixture
    async def setup(self, client: AsyncClient, test_db: AsyncSession) -> dict:
        """建立管理員、被舉報用戶（40 分）與 PENDING 舉報"""
        admin = User(
            id=uuid.uuid4(),
            email="approve_admin@example.com",
            password_hash=get_password_hash("Admin123"),
            date_of_birth=date(1990, 1, 1),
            is_active=True,
            is_admin=True,
        )
        reporter = make_user("approve_reporter@example.com", 50)
        reported = make_user("approve_reported@example.com", 40)
        test_db.add_all([admin, reporter, reported])
        await test_db.commit()  # 先寫入用戶，Report 的 FK 才有效

        report = Report(
            id=uuid.uuid4(),
            reporter_id=reporter.id,
            reported_user_id=reported.id,
            report_type="SPAM",
            reason="測試舉報",
        )
        test_db.add(report)
        await test_db.commit()

        response = await client.post(
            "/api/auth/admin-login",
            json={"email": "approve_admin@example.com", "password": "Admin123"},
        )
        token = response.json()["access_token"]
        client.cookies.clear()

        return {
            "headers": {"Authorization": f"Bearer {token}"},
            "report": report,
            "reported": reported,
        }

    async def test_approved_report_deducts_score(
        self, client: AsyncClient, test_db: AsyncSession, setup: dict
    ):
        """成立舉報後被舉報用戶 -10 且警告次數 +1"""
        response = await client.post(
            f"/api/admin/reports/{setup['report'].id}/review",
            json={"status": "APPROVED", "admin_notes": "違規屬實"},
            headers=setup["headers"],
        )

        assert response.status_code == 200
        scores = await get_scores(test_db, [setup["reported"]])
        assert scores["approve_reported@example.com"] == 30

        result = await test_db.execute(
            select(User.warning_count).where(User.id == setup["reported"].id)
        )
        assert result.scalar_one() == 1

    async def test_re_approving_does_not_deduct_twice(
        self, client: AsyncClient, test_db: AsyncSession, setup: dict
    ):
        """重複成立同一舉報不重複扣分、不重複累加警告"""
        for _ in range(2):
            response = await client.post(
                f"/api/admin/reports/{setup['report'].id}/review",
                json={"status": "APPROVED"},
                headers=setup["headers"],
            )
            assert response.status_code == 200

        scores = await get_scores(test_db, [setup["reported"]])
        assert scores["approve_reported@example.com"] == 30

        result = await test_db.execute(
            select(User.warning_count).where(User.id == setup["reported"].id)
        )
        assert result.scalar_one() == 1
