"""信任分數每日恢復服務

低於預設分（50）的用戶每日 +1，恢復到預設分為止：
- 解決被誤報用戶因配對權重降低、難以透過互動翻身的惡性循環
- 上限為預設分：真正違規者無法靠時間恢復高信任狀態
- 排除軟刪除（deleted_at）與被停權（is_active=False）用戶
- 以 Redis 日期鎖（SET NX）確保每日只執行一次（應用重啟不重複加分）
- 每筆恢復寫入 trust_score_logs 審計日誌

背景任務模式同 account_cleanup：lifespan 啟動/停止，先等待再執行。
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import func

from app.core.database import AsyncSessionLocal
from app.models.trust_score_log import TrustScoreLog
from app.models.user import User
from app.services.redis_client import redis_client
from app.services.trust_score import TrustScoreService

logger = logging.getLogger(__name__)

DAILY_RECOVERY_ACTION = "daily_recovery"

# 檢查間隔（秒）：每小時檢查當日是否已執行
RECOVERY_CHECK_INTERVAL_SECONDS = 60 * 60

# Redis 日期鎖 TTL（48 小時，跨日後自動過期）
RECOVERY_LOCK_TTL_SECONDS = 48 * 60 * 60

_recovery_task: asyncio.Task | None = None


def _lock_key(date_str: str) -> str:
    return f"trust:daily_recovery:{date_str}"


async def apply_daily_recovery(db: AsyncSession | None = None) -> int:
    """為低於預設分的活躍用戶加分（含審計日誌）

    Note:
        不含防重複執行保護，呼叫端需確保每日只執行一次
        （見 run_daily_recovery_once）。

    Args:
        db: 測試時可注入 session；未提供時自建

    Returns:
        int: 本次恢復的用戶數
    """
    if db is not None:
        return await _apply(db)

    async with AsyncSessionLocal() as session:
        return await _apply(session)


async def _apply(db: AsyncSession) -> int:
    adjustment = TrustScoreService.ADJUSTMENTS[DAILY_RECOVERY_ACTION]

    # 批次原子更新並取回新分數，供審計日誌寫入（同一交易提交）
    result = await db.execute(
        update(User)
        .where(
            User.trust_score < TrustScoreService.DEFAULT_SCORE,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        .values(
            trust_score=func.least(TrustScoreService.DEFAULT_SCORE, User.trust_score + adjustment)
        )
        .returning(User.id, User.trust_score)
    )
    rows = result.all()

    db.add_all(
        TrustScoreLog(
            user_id=row.id,
            action=DAILY_RECOVERY_ACTION,
            adjustment=adjustment,
            new_score=row.trust_score,
            reason="每日自動恢復",
        )
        for row in rows
    )
    await db.commit()

    return len(rows)


async def run_daily_recovery_once(db: AsyncSession | None = None) -> int:
    """若今日尚未執行則執行恢復（Redis SET NX 日期鎖防重複）

    Args:
        db: 測試時可注入 session；未提供時自建

    Returns:
        int: 本次恢復的用戶數（已執行過或 Redis 不可用時為 0）
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    try:
        redis_conn = await redis_client.get_connection()
        acquired = await redis_conn.set(
            _lock_key(today), "1", nx=True, ex=RECOVERY_LOCK_TTL_SECONDS
        )
    except Exception as e:
        # 無鎖時跳過本輪（寧可延後也不重複加分），下一輪再試
        logger.warning(f"Trust score recovery skipped, Redis unavailable: {e}")
        return 0

    if not acquired:
        return 0

    try:
        recovered = await apply_daily_recovery(db)
        if recovered:
            logger.info(f"Trust score daily recovery: +1 for {recovered} users")
        return recovered
    except Exception:
        # 執行失敗時釋放日期鎖，讓下一輪重試
        with contextlib.suppress(Exception):
            await redis_conn.delete(_lock_key(today))
        raise


async def start_recovery_task() -> None:
    """啟動定期恢復任務（lifespan 啟動時呼叫）"""
    global _recovery_task
    if _recovery_task is None:
        _recovery_task = asyncio.create_task(_periodic_recovery())
        logger.info("Started trust score recovery task")


async def stop_recovery_task() -> None:
    """停止定期恢復任務（lifespan 關閉時呼叫）"""
    global _recovery_task
    if _recovery_task is not None:
        _recovery_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _recovery_task
        _recovery_task = None
        logger.info("Stopped trust score recovery task")


async def _periodic_recovery() -> None:
    """每小時檢查當日是否已執行（先等待再執行，避免啟動時搶占資源）"""
    while True:
        try:
            await asyncio.sleep(RECOVERY_CHECK_INTERVAL_SECONDS)
            await run_daily_recovery_once()
        except asyncio.CancelledError:
            logger.info("Trust score recovery task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in trust score recovery: {e}", exc_info=True)
