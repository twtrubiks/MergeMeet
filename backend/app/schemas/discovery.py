"""探索與配對相關的 Schema"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProfileCard(BaseModel):
    """探索卡片顯示的個人檔案資訊"""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    display_name: str
    age: int
    gender: str | None
    bio: str | None
    location_name: str | None
    distance_km: float | None = Field(None, description="距離（公里）")
    interests: list[str] = []
    photos: list[str] = []  # 照片 URL 列表
    match_score: float | None = Field(None, description="配對分數（0-100）")


class LikeAction(BaseModel):
    """喜歡動作"""

    user_id: UUID


class LikeResponse(BaseModel):
    """喜歡回應"""

    model_config = ConfigDict(from_attributes=True)

    liked: bool
    is_match: bool
    match_id: UUID | None = None


class MatchSummary(BaseModel):
    """配對摘要"""

    model_config = ConfigDict(from_attributes=True)

    match_id: UUID
    matched_user: ProfileCard
    matched_at: datetime
    unread_count: int = 0


class MatchDetail(BaseModel):
    """配對詳細資訊"""

    model_config = ConfigDict(from_attributes=True)

    match_id: UUID
    user1_id: UUID
    user2_id: UUID
    status: str
    matched_at: datetime
    unmatched_at: datetime | None = None
    unmatched_by: UUID | None = None
