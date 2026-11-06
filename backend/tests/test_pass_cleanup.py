"""Pass 記錄清理測試

驗證 purge_old_passes：刪除 7 天前的跳過記錄，保留期內的不受影響。
"""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.match import Pass
from app.models.user import User
from app.services import pass_cleanup
from app.services.pass_cleanup import (
    CLEANUP_INTERVAL_SECONDS,
    PASS_RETENTION_DAYS,
    purge_old_passes,
    start_cleanup_task,
    stop_cleanup_task,
)


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

    async def test_retention_boundary(self, test_db: AsyncSession):
        """剛超過保留期 1 分鐘的刪除，還差 1 分鐘的保留"""
        alice = make_user("alice_edge@example.com")
        bob = make_user("bob_edge@example.com")
        carol = make_user("carol_edge@example.com")
        test_db.add_all([alice, bob, carol])
        await test_db.commit()

        now = datetime.now(UTC)
        expired = Pass(
            from_user_id=alice.id,
            to_user_id=bob.id,
            passed_at=now - timedelta(days=PASS_RETENTION_DAYS, minutes=1),
        )
        kept = Pass(
            from_user_id=alice.id,
            to_user_id=carol.id,
            passed_at=now - timedelta(days=PASS_RETENTION_DAYS) + timedelta(minutes=1),
        )
        test_db.add_all([expired, kept])
        await test_db.commit()

        assert await purge_old_passes(test_db) == 1
        result = await test_db.execute(select(Pass.id))
        assert {row[0] for row in result.all()} == {kept.id}

    async def test_own_session_when_not_injected(self, test_db: AsyncSession, monkeypatch):
        """未注入 session 時自建 session 並提交（正式環境背景任務走的路徑）"""
        alice = make_user("alice_own@example.com")
        bob = make_user("bob_own@example.com")
        test_db.add_all([alice, bob])
        await test_db.commit()
        test_db.add(make_pass(alice, bob, days_ago=PASS_RETENTION_DAYS + 1))
        await test_db.commit()
        monkeypatch.setattr(
            pass_cleanup,
            "AsyncSessionLocal",
            async_sessionmaker(test_db.bind, expire_on_commit=False),
        )

        assert await purge_old_passes() == 1
        result = await test_db.execute(select(Pass.id))
        assert result.all() == []


class TestPassCleanupTask:
    """背景任務：啟動／停止與每日迴圈"""

    async def test_start_is_idempotent_and_stop_cancels(self, monkeypatch):
        running = asyncio.Event()

        async def _forever():
            running.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(pass_cleanup, "_periodic_cleanup", _forever)

        await start_cleanup_task()
        task = pass_cleanup._cleanup_task
        await start_cleanup_task()  # 已啟動時不重複建立
        assert pass_cleanup._cleanup_task is task
        await asyncio.wait_for(running.wait(), timeout=1)  # 任務沒啟動時直接失敗而非卡住

        await stop_cleanup_task()

        assert task.cancelled()
        assert pass_cleanup._cleanup_task is None

    async def test_stop_without_start_is_noop(self):
        await stop_cleanup_task()
        assert pass_cleanup._cleanup_task is None

    async def test_periodic_loop_survives_errors_until_cancelled(self, monkeypatch):
        """每輪先等待間隔再執行；單輪失敗不中止迴圈，取消時結束"""
        sleeps: list[int] = []
        runs = 0
        real_sleep = asyncio.sleep

        async def _sleep(seconds):
            sleeps.append(seconds)
            await real_sleep(0)  # 讓出控制權，迴圈不結束時 wait_for 才能逾時
            if len(sleeps) >= 3:
                raise asyncio.CancelledError

        async def _purge():
            nonlocal runs
            runs += 1
            if runs == 1:
                raise RuntimeError("第一輪失敗")
            return 0

        monkeypatch.setattr(pass_cleanup.asyncio, "sleep", _sleep)
        monkeypatch.setattr(pass_cleanup, "purge_old_passes", _purge)

        await asyncio.wait_for(pass_cleanup._periodic_cleanup(), timeout=1)

        assert sleeps == [CLEANUP_INTERVAL_SECONDS] * 3
        assert runs == 2
