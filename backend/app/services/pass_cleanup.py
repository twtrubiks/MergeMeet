"""Pass 記錄清理服務

跳過記錄僅在 24 小時內影響探索結果（以 passed_at 計算），
保留 7 天緩衝後即可刪除，避免資料表無限增長。

背景任務模式同 account_cleanup：lifespan 啟動/停止，先等待再執行。
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.match import Pass

logger = logging.getLogger(__name__)

# 保留天數（查詢僅用到 24 小時內的記錄，7 天提供充足緩衝）
PASS_RETENTION_DAYS = 7

# 清理任務執行間隔（秒）：每日一次
CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60

_cleanup_task: asyncio.Task | None = None


async def purge_old_passes(db: AsyncSession | None = None) -> int:
    """刪除保留期外的跳過記錄

    Args:
        db: 測試時可注入 session；未提供時自建

    Returns:
        int: 本次刪除的記錄數
    """
    if db is not None:
        return await _purge(db)

    async with AsyncSessionLocal() as session:
        return await _purge(session)


async def _purge(db: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=PASS_RETENTION_DAYS)
    result = await db.execute(delete(Pass).where(Pass.passed_at < cutoff))
    await db.commit()
    return result.rowcount or 0


async def start_cleanup_task() -> None:
    """啟動定期清理任務（lifespan 啟動時呼叫）"""
    global _cleanup_task
    if _cleanup_task is None:
        _cleanup_task = asyncio.create_task(_periodic_cleanup())
        logger.info("Started pass cleanup task")


async def stop_cleanup_task() -> None:
    """停止定期清理任務（lifespan 關閉時呼叫）"""
    global _cleanup_task
    if _cleanup_task is not None:
        _cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _cleanup_task
        _cleanup_task = None
        logger.info("Stopped pass cleanup task")


async def _periodic_cleanup() -> None:
    """定期清除過期跳過記錄（先等待再執行，避免啟動時搶占資源）"""
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            purged = await purge_old_passes()
            if purged:
                logger.info(f"Pass cleanup: purged {purged} old pass records")
        except asyncio.CancelledError:
            logger.info("Pass cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in pass cleanup: {e}", exc_info=True)
