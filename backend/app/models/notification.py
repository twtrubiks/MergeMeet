"""通知模型 - 持久化用戶通知"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime, timezone

from app.core.database import Base


class Notification(Base):
    """通知模型

    支援三種通知類型：
    - notification_message: 新訊息通知
    - notification_match: 新配對通知
    - notification_liked: 有人喜歡你通知
    """
    __tablename__ = "notifications"

    # 主鍵
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 用戶關聯
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 通知類型
    type = Column(String(50), nullable=False)

    # 通知內容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)

    # 額外資料 (JSON 格式)
    # notification_message: { match_id, sender_id, sender_name, preview }
    # notification_match: { match_id, matched_user_id, matched_user_name, matched_user_avatar }
    # notification_liked: {} (保持神秘感，不透露是誰)
    data = Column(JSONB, default=dict)

    # 狀態
    is_read = Column(Boolean, default=False, index=True)

    # 時間戳記
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # 關聯
    user = relationship("User", back_populates="notifications")

    # 複合索引優化查詢
    __table_args__ = (
        Index('idx_notifications_user_unread', 'user_id', 'is_read'),
        Index('idx_notifications_user_created', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Notification {self.type} for user {self.user_id}>"
