"""帳號到期清理服務測試

API 層的刪除帳號與寬限期流程見 test_delete_account.py；
這裡測試 purge_expired_accounts 的邊界、Redis 清理、單筆失敗與背景任務。
"""

import asyncio
import shutil
import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.match import Match
from app.models.user import User
from app.services import account_cleanup
from app.services.account_cleanup import (
    CLEANUP_INTERVAL_SECONDS,
    GRACE_PERIOD_DAYS,
    purge_expired_accounts,
    start_cleanup_task,
    stop_cleanup_task,
)


def make_deleted_user(email: str, deleted_at: datetime) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        password_hash="dummy_hash",
        date_of_birth=date(1995, 1, 1),
        is_active=False,
        deleted_at=deleted_at,
    )


@pytest.fixture
def redis_conn(monkeypatch):
    """替換 redis_client，記錄清理時刪除的 key"""
    conn = AsyncMock()
    client = AsyncMock()
    client.get_connection = AsyncMock(return_value=conn)
    monkeypatch.setattr(account_cleanup, "redis_client", client)
    return conn


async def remaining_emails(db: AsyncSession) -> set[str]:
    result = await db.execute(select(User.email))
    return {row[0] for row in result.all()}


@pytest.mark.asyncio
class TestPurgeExpiredAccounts:
    async def test_grace_period_boundary(self, test_db: AsyncSession, redis_conn):
        """剛超過寬限期 1 分鐘的清除，還差 1 分鐘的保留，未刪除的帳號不受影響"""
        now = datetime.now(UTC)
        expired = make_deleted_user(
            "expired@example.com", now - timedelta(days=GRACE_PERIOD_DAYS, minutes=1)
        )
        in_grace = make_deleted_user(
            "in_grace@example.com", now - timedelta(days=GRACE_PERIOD_DAYS) + timedelta(minutes=1)
        )
        active = User(
            email="active@example.com",
            password_hash="dummy_hash",
            date_of_birth=date(1995, 1, 1),
        )
        test_db.add_all([expired, in_grace, active])
        await test_db.commit()

        assert await purge_expired_accounts(test_db) == 1
        assert await remaining_emails(test_db) == {"in_grace@example.com", "active@example.com"}

    async def test_cleans_chat_dirs_of_all_matches(self, test_db: AsyncSession, redis_conn):
        """無論是配對的 user1 或 user2，所有配對的聊天圖片目錄都清除；計數為實際清除的帳號數"""
        deleted_at = datetime.now(UTC) - timedelta(days=31)
        purged = make_deleted_user("purged@example.com", deleted_at)
        other = make_deleted_user("other_purged@example.com", deleted_at)
        friend_a = User(
            email="friend_a@example.com", password_hash="x", date_of_birth=date(1995, 1, 1)
        )
        friend_b = User(
            email="friend_b@example.com", password_hash="x", date_of_birth=date(1995, 1, 1)
        )
        # matches 限制 user1_id < user2_id：friend_b < purged < friend_a
        friend_b.id = uuid.UUID(int=1)
        purged.id = uuid.UUID(int=2)
        friend_a.id = uuid.UUID(int=3)
        test_db.add_all([purged, other, friend_a, friend_b])
        await test_db.commit()
        as_user1 = Match(user1_id=purged.id, user2_id=friend_a.id)
        as_user2 = Match(user1_id=friend_b.id, user2_id=purged.id)
        unrelated = Match(user1_id=friend_b.id, user2_id=friend_a.id)
        test_db.add_all([as_user1, as_user2, unrelated])
        await test_db.commit()

        chat_dirs = {}
        for match in (as_user1, as_user2, unrelated):
            chat_dir = account_cleanup.file_storage.chat_dir / str(match.id)
            chat_dir.mkdir(parents=True, exist_ok=True)
            chat_dirs[match.id] = chat_dir

        try:
            assert await purge_expired_accounts(test_db) == 2

            assert not chat_dirs[as_user1.id].exists()
            assert not chat_dirs[as_user2.id].exists()
            assert chat_dirs[unrelated.id].exists()
        finally:
            for chat_dir in chat_dirs.values():
                shutil.rmtree(chat_dir, ignore_errors=True)

    async def test_cleans_token_invalidation_key(self, test_db: AsyncSession, redis_conn):
        """清除該用戶在 Redis 中沒有自動過期的 key"""
        user = make_deleted_user("redis_key@example.com", datetime.now(UTC) - timedelta(days=31))
        test_db.add(user)
        await test_db.commit()

        await purge_expired_accounts(test_db)

        redis_conn.delete.assert_awaited_once_with(f"token_invalidated:{user.id}")

    async def test_redis_failure_still_counts_as_purged(self, test_db: AsyncSession, redis_conn):
        """Redis 清理失敗不影響帳號清除"""
        redis_conn.delete.side_effect = ConnectionError("Redis down")
        test_db.add(
            make_deleted_user("redis_down@example.com", datetime.now(UTC) - timedelta(days=31))
        )
        await test_db.commit()

        assert await purge_expired_accounts(test_db) == 1
        assert await remaining_emails(test_db) == set()

    async def test_one_failure_does_not_stop_others(
        self, test_db: AsyncSession, redis_conn, monkeypatch
    ):
        """單筆清理失敗時跳過、不計入，其他帳號照常清理"""
        deleted_at = datetime.now(UTC) - timedelta(days=31)
        failing = make_deleted_user("failing@example.com", deleted_at)
        ok = make_deleted_user("ok@example.com", deleted_at)
        test_db.add_all([failing, ok])
        await test_db.commit()

        real_delete_dir = account_cleanup.file_storage.delete_user_photo_dir

        def _delete_dir(user_id: str) -> None:
            if user_id == str(failing.id):
                raise OSError("disk error")
            real_delete_dir(user_id)

        monkeypatch.setattr(account_cleanup.file_storage, "delete_user_photo_dir", _delete_dir)

        assert await purge_expired_accounts(test_db) == 1
        # 失敗的那筆在檔案清理前就已刪除資料列，只有成功的那筆會清 Redis
        redis_conn.delete.assert_awaited_once_with(f"token_invalidated:{ok.id}")

    async def test_own_session_when_not_injected(
        self, test_db: AsyncSession, redis_conn, monkeypatch
    ):
        """未注入 session 時自建 session（正式環境背景任務走的路徑）"""
        test_db.add(
            make_deleted_user("own_session@example.com", datetime.now(UTC) - timedelta(days=31))
        )
        await test_db.commit()
        monkeypatch.setattr(
            account_cleanup,
            "AsyncSessionLocal",
            async_sessionmaker(test_db.bind, expire_on_commit=False),
        )

        assert await purge_expired_accounts() == 1
        assert await remaining_emails(test_db) == set()


class TestAccountCleanupTask:
    """背景任務：啟動／停止與定期迴圈"""

    async def test_start_is_idempotent_and_stop_cancels(self, monkeypatch):
        running = asyncio.Event()

        async def _forever():
            running.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(account_cleanup, "_periodic_cleanup", _forever)

        await start_cleanup_task()
        task = account_cleanup._cleanup_task
        await start_cleanup_task()  # 已啟動時不重複建立
        assert account_cleanup._cleanup_task is task
        await asyncio.wait_for(running.wait(), timeout=1)  # 任務沒啟動時直接失敗而非卡住

        await stop_cleanup_task()

        assert task.cancelled()
        assert account_cleanup._cleanup_task is None

    async def test_stop_without_start_is_noop(self):
        await stop_cleanup_task()
        assert account_cleanup._cleanup_task is None

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

        monkeypatch.setattr(account_cleanup.asyncio, "sleep", _sleep)
        monkeypatch.setattr(account_cleanup, "purge_expired_accounts", _purge)

        await asyncio.wait_for(account_cleanup._periodic_cleanup(), timeout=1)

        assert sleeps == [CLEANUP_INTERVAL_SECONDS] * 3
        assert runs == 2
