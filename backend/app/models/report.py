"""舉報相關資料模型"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Report(Base):
    """舉報記錄模型"""
    __tablename__ = "reports"

    # 主鍵
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 舉報關係
    reporter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reported_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 舉報內容 (INAPPROPRIATE, HARASSMENT, FAKE, SCAM, OTHER)
    report_type = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)

    # 處理狀態 (PENDING, UNDER_REVIEW, RESOLVED, DISMISSED)
    status = Column(String(20), default="PENDING")

    # 管理員備註
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 資料庫約束：不能舉報自己
    __table_args__ = (
        CheckConstraint('reporter_id != reported_user_id', name='no_self_report'),
    )

    def __repr__(self):
        return f"<Report {self.id} by {self.reporter_id} against {self.reported_user_id}>"
