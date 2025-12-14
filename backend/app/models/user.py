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

    # 信任機制
    # TODO: 信任分數系統尚未實現完整邏輯
    # 預計功能：
    # - 提高分數：完成驗證、正常互動、被喜歡
    # - 降低分數：被舉報、發送違規內容、被封鎖
    # - 影響：低分用戶在探索中排序靠後，極低分自動限制功能
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
