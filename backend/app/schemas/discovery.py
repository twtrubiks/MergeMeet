"""探索與配對相關的 Schema"""

from datetime import datetime
from typing import Literal
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
    common_interests: list[str] = Field(
        default_factory=list, description="與瀏覽者的共同興趣（配對理由），依候選人興趣順序"
    )
    photos: list[str] = []  # 照片 URL 列表
    match_score: float | None = Field(None, description="配對分數（0-100）")
    last_active: datetime | None = Field(
        None, description="最後活躍時間（目前僅配對列表回傳，供前端顯示在線狀態）"
    )


class ExpandSuggestion(BaseModel):
    """空池時的偏好放寬建議（前端一鍵套用，後端不自動改偏好）"""

    type: Literal["distance", "age"]
    additional_candidates: int = Field(..., ge=1, description="放寬後可多看到的候選人數")
    # type == "distance"
    current_max_distance_km: int | None = None
    suggested_max_distance_km: int | None = None
    # type == "age"
    current_min_age: int | None = None
    current_max_age: int | None = None
    suggested_min_age: int | None = None
    suggested_max_age: int | None = None


class ExpandSuggestionsResponse(BaseModel):
    suggestions: list[ExpandSuggestion] = []


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


class PassResponse(BaseModel):
    """跳過用戶回應"""

    passed: bool
    message: str


class UnmatchResponse(BaseModel):
    """取消配對回應"""

    message: str


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
