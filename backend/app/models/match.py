"""配對相關資料模型"""
from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Like(Base):
    """喜歡記錄"""
    __tablename__ = "likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 約束：不能喜歡自己，且同一對用戶只能有一個喜歡記錄
    __table_args__ = (
        CheckConstraint('from_user_id != to_user_id', name='no_self_like'),
        UniqueConstraint('from_user_id', 'to_user_id', name='unique_like'),
    )

    def __repr__(self):
        return f"<Like {self.from_user_id} -> {self.to_user_id}>"


class Pass(Base):
    """跳過記錄

    記錄用戶跳過操作，24 小時內跳過的用戶不會再次出現。
    24 小時後可重新配對（類似 Tinder 做法），給用戶第二次機會。

    簡化實現：不需要 expires_at 欄位，直接在查詢時用 passed_at 計算。

    效能優化建議（未來可改善）：
    - 資料庫會持續累積跳過記錄，可用背景任務定期清理 7 天前的記錄
    - 方案 1: APScheduler（輕量級，適合單實例）
      @scheduler.scheduled_job('cron', hour=3)  # 每天凌晨 3 點執行
      async def cleanup_old_passes():
          cutoff = datetime.now() - timedelta(days=7)
          await db.execute(delete(Pass).where(Pass.passed_at < cutoff))

    - 方案 2: Celery（適合分散式部署）
      @celery.task
      def cleanup_old_passes():
          # 定期清理邏輯

    - 方案 3: PostgreSQL 自動清理（最簡單）
      CREATE INDEX ix_passes_cleanup ON passes(passed_at)
      WHERE passed_at < NOW() - INTERVAL '7 days';
      -- 然後定期 VACUUM 即可

    目前簡化版無背景清理，資料表會持續增長但影響不大（索引已優化查詢）。
    """
    __tablename__ = "passes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    passed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 約束：不能跳過自己
    __table_args__ = (
        CheckConstraint('from_user_id != to_user_id', name='no_self_pass'),
        UniqueConstraint('from_user_id', 'to_user_id', name='unique_pass'),
    )

    def __repr__(self):
        return f"<Pass {self.from_user_id} -> {self.to_user_id}>"


class Match(Base):
    """配對記錄"""
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 用戶 ID（保證 user1_id < user2_id，避免重複）
    user1_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 配對狀態: ACTIVE(活躍), UNMATCHED(已取消)
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)

    # 時間戳記
    matched_at = Column(DateTime(timezone=True), server_default=func.now())
    unmatched_at = Column(DateTime(timezone=True), nullable=True)
    unmatched_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 關聯
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")

    # 約束：保證 user1_id < user2_id，避免重複配對
    __table_args__ = (
        CheckConstraint('user1_id < user2_id', name='user_order'),
        UniqueConstraint('user1_id', 'user2_id', name='unique_match'),
    )

    def __repr__(self):
        return f"<Match {self.user1_id} <-> {self.user2_id} ({self.status})>"


class Message(Base):
    """聊天訊息"""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 訊息內容
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="TEXT")  # TEXT, IMAGE, GIF

    # 狀態
    is_read = Column(DateTime(timezone=True), nullable=True)  # 讀取時間
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # 刪除時間

    # 時間戳記
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 關聯
    match = relationship("Match", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"


class BlockedUser(Base):
    """封鎖用戶記錄"""
    __tablename__ = "blocked_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 約束：不能封鎖自己，且同一對用戶只能有一個封鎖記錄
    __table_args__ = (
        CheckConstraint('blocker_id != blocked_id', name='no_self_block'),
        UniqueConstraint('blocker_id', 'blocked_id', name='unique_block'),
    )

    def __repr__(self):
        return f"<BlockedUser {self.blocker_id} blocked {self.blocked_id}>"
