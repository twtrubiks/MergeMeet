"""探索與配對相關的 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ProfileCard(BaseModel):
    """探索卡片顯示的個人檔案資訊"""
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    display_name: str
    age: int
    gender: Optional[str]
    bio: Optional[str]
    location_name: Optional[str]
    distance_km: Optional[float] = Field(None, description="距離（公里）")
    interests: List[str] = []
    photos: List[str] = []  # 照片 URL 列表
    match_score: Optional[float] = Field(None, description="配對分數（0-100）")


class LikeAction(BaseModel):
    """喜歡動作"""
    user_id: UUID


class LikeResponse(BaseModel):
    """喜歡回應"""
    model_config = ConfigDict(from_attributes=True)

    liked: bool
    is_match: bool
    match_id: Optional[UUID] = None


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
    unmatched_at: Optional[datetime] = None
    unmatched_by: Optional[UUID] = None
