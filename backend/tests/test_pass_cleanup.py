"""Pass 記錄清理測試

驗證 purge_old_passes：刪除 7 天前的跳過記錄，保留期內的不受影響。
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Pass
from app.models.user import User
from app.services.pass_cleanup import PASS_RETENTION_DAYS, purge_old_passes


def make_user(email: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash="dummy_hash",
        date_of_birth=date(1995, 1, 1),
        is_active=True,
    )


def make_pass(from_user: User, to_user: User, days_ago: int) -> Pass:
    return Pass(
        id=uuid.uuid4(),
        from_user_id=from_user.id,
        to_user_id=to_user.id,
        passed_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


@pytest.mark.asyncio
class TestPassCleanup:
    """purge_old_passes：刪除保留期外的跳過記錄"""

    async def test_purges_only_old_passes(self, test_db: AsyncSession):
        """超過保留期的記錄刪除，期限內的保留"""
        alice = make_user("alice_pass@example.com")
        bob = make_user("bob_pass@example.com")
        carol = make_user("carol_pass@example.com")
        test_db.add_all([alice, bob, carol])
        await test_db.commit()

        old_pass = make_pass(alice, bob, days_ago=PASS_RETENTION_DAYS + 1)
        recent_pass = make_pass(alice, carol, days_ago=1)
        today_pass = make_pass(bob, carol, days_ago=0)
        test_db.add_all([old_pass, recent_pass, today_pass])
        await test_db.commit()

        purged = await purge_old_passes(test_db)

        assert purged == 1
        result = await test_db.execute(select(Pass.id))
        remaining_ids = {row[0] for row in result.all()}
        assert remaining_ids == {recent_pass.id, today_pass.id}

    async def test_no_old_passes_is_noop(self, test_db: AsyncSession):
        """無過期記錄時不動作"""
        alice = make_user("alice_noop@example.com")
        bob = make_user("bob_noop@example.com")
        test_db.add_all([alice, bob])
        await test_db.commit()

        test_db.add(make_pass(alice, bob, days_ago=1))
        await test_db.commit()

        assert await purge_old_passes(test_db) == 0

    async def test_empty_table_is_noop(self, test_db: AsyncSession):
        """空表執行不報錯"""
        assert await purge_old_passes(test_db) == 0
