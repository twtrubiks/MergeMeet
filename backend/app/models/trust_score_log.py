"""信任分數審計日誌模型"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class TrustScoreLog(Base):
    """信任分數變更日誌

    每次 trust_score 變更時同交易寫入，供用戶爭議追溯與管理員審計。
    """

    __tablename__ = "trust_score_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 行為類型（TrustScoreService.ADJUSTMENTS 的 key）
    action = Column(String(50), nullable=False)
    # 名目調整值；實際變化受 0-100 邊界與恢復上限影響，以 new_score 為準
    adjustment = Column(Integer, nullable=False)
    new_score = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 複合索引：依用戶查詢變更歷史（最新在前）
    __table_args__ = (Index("ix_trust_score_logs_user_created", "user_id", "created_at"),)

    def __repr__(self):
        return (
            f"<TrustScoreLog {self.user_id} {self.action} {self.adjustment:+d} -> {self.new_score}>"
        )
