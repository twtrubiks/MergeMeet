"""內容審核相關資料模型"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class SensitiveWord(Base):
    """敏感詞模型"""
    __tablename__ = "sensitive_words"

    # 主鍵
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 敏感詞內容
    word = Column(String(100), nullable=False, unique=True, index=True)

    # 分類
    # SEXUAL, SCAM, HARASSMENT, VIOLENCE, PERSONAL_INFO, OTHER
    category = Column(String(50), nullable=False)

    # 嚴重程度
    severity = Column(String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL

    # 處理動作
    action = Column(String(20), nullable=False, default="WARN")  # WARN, REJECT, AUTO_BAN

    # 是否為正則表達式
    is_regex = Column(Boolean, default=False)

    # 描述說明
    description = Column(Text, nullable=True)

    # 是否啟用
    is_active = Column(Boolean, default=True, index=True)

    # 創建者（管理員）
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SensitiveWord {self.word} ({self.category})>"


class ContentAppeal(Base):
    """內容申訴模型"""
    __tablename__ = "content_appeals"

    # 主鍵
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 申訴者
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 申訴類型
    appeal_type = Column(String(50), nullable=False)  # MESSAGE, PROFILE, PHOTO

    # 被拒絕的內容
    rejected_content = Column(Text, nullable=False)

    # 觸發的違規項目
    violations = Column(Text, nullable=False)  # JSON array as string

    # 申訴理由
    reason = Column(Text, nullable=False)

    # 處理狀態 (PENDING, APPROVED, REJECTED)
    status = Column(String(20), default="PENDING", index=True)

    # 管理員回覆
    admin_response = Column(Text, nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ContentAppeal {self.id} by {self.user_id} ({self.status})>"


class ModerationLog(Base):
    """審核日誌模型 - 記錄所有審核動作"""
    __tablename__ = "moderation_logs"

    # 主鍵
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 被審核的用戶
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 內容類型
    content_type = Column(String(50), nullable=False)  # MESSAGE, PROFILE, PHOTO

    # 原始內容
    original_content = Column(Text, nullable=False)

    # 審核結果
    is_approved = Column(Boolean, nullable=False)

    # 違規項目
    violations = Column(Text, nullable=True)  # JSON array as string

    # 觸發的敏感詞 ID
    triggered_word_ids = Column(Text, nullable=True)  # JSON array of UUIDs as string

    # 處理動作 (APPROVED, REJECTED, WARNING_ISSUED, USER_BANNED)
    action_taken = Column(String(50), nullable=False)

    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<ModerationLog {self.id} for user {self.user_id}>"
