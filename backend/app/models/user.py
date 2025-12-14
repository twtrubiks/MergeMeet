"""用戶相關資料模型"""
from sqlalchemy import Column, String, Boolean, DateTime, Date, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class User(Base):
    """用戶模型"""
    __tablename__ = "users"

    # 主鍵
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 認證資訊
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False)
    date_of_birth = Column(Date, nullable=False)

    # 密碼重置
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # 信任機制（已實現：TrustScoreService）
    # 功能：
    # - 提高分數：Email 驗證 +5、被喜歡 +1、配對成功 +2
    # - 降低分數：被舉報 -5、舉報確認 -10、違規內容 -3、被封鎖 -2
    # - 影響：低分用戶在探索中排序靠後（配對算法 5 分權重）
    # - 限制：< 20 分用戶每日訊息上限 20 則
    trust_score = Column(Integer, default=50)
    warning_count = Column(Integer, default=0)

    # 帳號狀態
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    banned_until = Column(DateTime(timezone=True), nullable=True)

    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 關聯
    profile = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Notification.created_at)"
    )

    def __repr__(self):
        return f"<User {self.email}>"
