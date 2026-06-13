"""帳號到期清理服務

刪除帳號功能：用戶請求刪除後進入寬限期（User.deleted_at 標記），
寬限期內重新登入可復原；到期後由此服務永久刪除資料庫資料
（關聯表均為 ondelete=CASCADE 連帶清除）、照片檔案與 Redis 記錄。
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.match import Match
from app.models.user import User
from app.services.file_storage import file_storage
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

# 寬限期天數（login 復原與到期清理共用）
GRACE_PERIOD_DAYS = 30

# 清理任務執行間隔（秒）
CLEANUP_INTERVAL_SECONDS = 6 * 60 * 60

_cleanup_task: asyncio.Task | None = None


async def purge_expired_accounts(db: AsyncSession | None = None) -> int:
    """永久刪除寬限期已過的帳號

    Args:
        db: 測試時可注入 session；未提供時自建

    Returns:
        int: 本次清除的帳號數
    """
    if db is not None:
        return await _purge(db)

    async with AsyncSessionLocal() as session:
        return await _purge(session)


async def _purge(db: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=GRACE_PERIOD_DAYS)
    result = await db.execute(
        select(User).where(User.deleted_at.is_not(None), User.deleted_at < cutoff)
    )
    users = result.scalars().all()

    purged = 0
    for user in users:
        user_id = str(user.id)
        try:
            # 先取出涉及的配對 ID，刪除後才能清理聊天圖片目錄
            match_result = await db.execute(
                select(Match.id).where(or_(Match.user1_id == user.id, Match.user2_id == user.id))
            )
            match_ids = [str(match_id) for match_id in match_result.scalars().all()]

            # 關聯表均為 ondelete=CASCADE，刪除 User row 即連帶清除
            await db.delete(user)
            await db.commit()

            file_storage.delete_user_photo_dir(user_id)
            for match_id in match_ids:
                file_storage.delete_chat_image_dir(match_id)

            await _cleanup_redis_keys(user_id)

            purged += 1
            logger.info(f"Purged expired account {user_id}")
        except Exception as e:
            # 單筆失敗不影響其他帳號的清理
            await db.rollback()
            logger.error(f"Failed to purge account {user_id}: {e}", exc_info=True)

    return purged


async def _cleanup_redis_keys(user_id: str) -> None:
    """清除該用戶殘留的 Redis Key（其餘 key 均有 TTL 會自動過期）"""
    try:
        redis_conn = await redis_client.get_connection()
        await redis_conn.delete(f"token_invalidated:{user_id}")
    except Exception as e:
        logger.warning(f"Failed to clean Redis keys for user {user_id}: {e}")


async def start_cleanup_task() -> None:
    """啟動定期清理任務（lifespan 啟動時呼叫）"""
    global _cleanup_task
    if _cleanup_task is None:
        _cleanup_task = asyncio.create_task(_periodic_cleanup())
        logger.info("Started account cleanup task")


async def stop_cleanup_task() -> None:
    """停止定期清理任務（lifespan 關閉時呼叫）"""
    global _cleanup_task
    if _cleanup_task is not None:
        _cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _cleanup_task
        _cleanup_task = None
        logger.info("Stopped account cleanup task")


async def _periodic_cleanup() -> None:
    """定期清除到期帳號（先等待再執行，避免啟動時搶占資源）"""
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            purged = await purge_expired_accounts()
            if purged:
                logger.info(f"Account cleanup: purged {purged} expired accounts")
        except asyncio.CancelledError:
            logger.info("Account cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in account cleanup: {e}", exc_info=True)
