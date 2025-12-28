"""信任分數服務

管理用戶信任分數的調整、查詢和限制功能。

Redis Key 設計:
- trust:daily_messages:{user_id}:{YYYY-MM-DD} - 每日訊息計數 (TTL: 86400 秒)
- chat:last_sender:{match_id} - 配對最後發送者 (TTL: 86400 秒)
- trust:positive_interaction:{match_id}:{YYYY-MM-DD} - 配對每日正向互動狀態 (TTL: 86400 秒)
- trust:positive_daily_total:{user_id}:{YYYY-MM-DD} - 用戶每日正向互動總獲得量 (TTL: 86400 秒)

分數範圍: 0-100
- 100: 高度信任用戶
- 50: 新用戶預設值
- 20: 限制閾值
- 0: 最低分（高度可疑）
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class TrustScoreService:
    """信任分數管理服務"""

    # 分數邊界
    MIN_SCORE = 0
    MAX_SCORE = 100
    DEFAULT_SCORE = 50

    # 限制閾值
    RESTRICTION_THRESHOLD = 20

    # 低信任用戶每日訊息上限
    LOW_TRUST_MESSAGE_LIMIT = 20

    # 分數調整值
    ADJUSTMENTS = {
        # 正向行為
        "email_verified": +5,
        "received_like": +1,
        "match_created": +2,
        "positive_interaction": +1,  # 預留：未來正常互動使用

        # 負向行為
        "reported": -5,
        "report_confirmed": -10,
        "content_violation": -3,
        "blocked": -2,
    }

    @classmethod
    async def adjust_score(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        action: str,
        reason: Optional[str] = None
    ) -> int:
        """
        調整用戶信任分數

        Args:
            db: 資料庫 Session
            user_id: 用戶 ID
            action: 行為類型（見 ADJUSTMENTS）
            reason: 調整原因（可選，用於日誌）

        Returns:
            調整後的分數

        Raises:
            ValueError: 未知的行為類型
        """
        if action not in cls.ADJUSTMENTS:
            raise ValueError(f"未知的行為類型: {action}")

        adjustment = cls.ADJUSTMENTS[action]

        # 查詢用戶
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"用戶不存在: {user_id}")

        # 計算新分數（確保在邊界內）
        new_score = user.trust_score + adjustment
        new_score = max(cls.MIN_SCORE, min(cls.MAX_SCORE, new_score))

        # 更新分數
        user.trust_score = new_score
        await db.commit()
        await db.refresh(user)

        return new_score

    @classmethod
    async def get_score(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> int:
        """
        獲取用戶當前信任分數

        Args:
            db: 資料庫 Session
            user_id: 用戶 ID

        Returns:
            信任分數（用戶不存在時返回預設值）
        """
        result = await db.execute(
            select(User.trust_score).where(User.id == user_id)
        )
        score = result.scalar_one_or_none()

        return score if score is not None else cls.DEFAULT_SCORE

    @classmethod
    async def is_restricted(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> bool:
        """
        檢查用戶是否處於受限狀態

        Args:
            db: 資料庫 Session
            user_id: 用戶 ID

        Returns:
            True 表示受限，False 表示正常
        """
        score = await cls.get_score(db, user_id)
        return score < cls.RESTRICTION_THRESHOLD

    @classmethod
    async def check_message_rate_limit(
        cls,
        user_id: uuid.UUID,
        trust_score: int,
        redis
    ) -> Tuple[bool, int]:
        """
        檢查低信任用戶的訊息速率限制

        Args:
            user_id: 用戶 ID
            trust_score: 用戶當前信任分數
            redis: Redis 連線

        Returns:
            (can_send, remaining): 是否可發送, 剩餘可發送數量
            - can_send: True 表示可以發送
            - remaining: 剩餘可發送數量（-1 表示無限制）
        """
        # 正常用戶無限制
        if trust_score >= cls.RESTRICTION_THRESHOLD:
            return True, -1

        # 獲取今日已發送數量
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"trust:daily_messages:{user_id}:{today}"

        count_str = await redis.get(key)
        current_count = int(count_str) if count_str else 0

        remaining = cls.LOW_TRUST_MESSAGE_LIMIT - current_count
        can_send = remaining > 0

        return can_send, max(0, remaining)

    @classmethod
    async def record_message_sent(
        cls,
        user_id: uuid.UUID,
        redis
    ) -> int:
        """
        記錄用戶發送訊息（用於限制計數）

        Args:
            user_id: 用戶 ID
            redis: Redis 連線

        Returns:
            今日已發送的訊息數量
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"trust:daily_messages:{user_id}:{today}"

        # 增加計數
        count = await redis.incr(key)

        # 設定過期時間（24 小時）
        await redis.expire(key, 86400)

        return count
