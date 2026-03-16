"""照片審核相關 Schema"""

from pydantic import BaseModel, Field


class PhotoReviewRequest(BaseModel):
    """照片審核請求"""

    status: str = Field(..., description="審核結果", pattern="^(APPROVED|REJECTED)$")
    rejection_reason: str | None = Field(
        None, max_length=500, description="拒絕原因（REJECTED 時必填）"
    )


class PhotoReviewResponse(BaseModel):
    """照片審核回應"""

    success: bool
    message: str
    photo_id: str
    status: str


class PendingPhotoResponse(BaseModel):
    """待審核照片回應"""

    id: str
    url: str
    thumbnail_url: str | None
    profile_id: str
    user_id: str
    user_email: str
    display_name: str
    moderation_status: str
    created_at: str | None
    file_size: int | None
    width: int | None
    height: int | None


class PendingPhotosListResponse(BaseModel):
    """待審核照片列表回應"""

    photos: list[PendingPhotoResponse]
    total: int
    page: int
    page_size: int


class PhotoDetailResponse(PendingPhotoResponse):
    """照片詳情回應（擴展 PendingPhotoResponse）"""

    rejection_reason: str | None = None
    reviewed_at: str | None = None
    mime_type: str | None = None
    auto_moderation_score: float | None = None
    auto_moderation_labels: str | None = None


class PhotoStatsResponse(BaseModel):
    """照片審核統計回應"""

    total_photos: int
    pending_photos: int
    approved_photos: int
    rejected_photos: int
    today_pending: int
    today_reviewed: int
