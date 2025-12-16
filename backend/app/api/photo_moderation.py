"""照片審核 API

管理員用於審核用戶上傳的照片。
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.services.photo_moderation import PhotoModerationService

router = APIRouter()


# ========== Schemas ==========


class PhotoReviewRequest(BaseModel):
    """照片審核請求"""
    status: str = Field(
        ...,
        description="審核結果",
        pattern="^(APPROVED|REJECTED)$"
    )
    rejection_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="拒絕原因（REJECTED 時必填）"
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
    thumbnail_url: Optional[str]
    profile_id: str
    user_id: str
    user_email: str
    display_name: str
    moderation_status: str
    created_at: Optional[str]
    file_size: Optional[int]
    width: Optional[int]
    height: Optional[int]


class PendingPhotosListResponse(BaseModel):
    """待審核照片列表回應"""
    photos: list[PendingPhotoResponse]
    total: int
    page: int
    page_size: int


class PhotoStatsResponse(BaseModel):
    """照片審核統計回應"""
    total_photos: int
    pending_photos: int
    approved_photos: int
    rejected_photos: int
    today_pending: int
    today_reviewed: int


# ========== API Endpoints ==========


@router.get("/pending", response_model=PendingPhotosListResponse)
async def get_pending_photos(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=100, description="每頁數量"),
    status: Optional[str] = Query(
        None,
        pattern="^(PENDING|APPROVED|REJECTED)$",
        description="篩選狀態"
    ),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得待審核照片列表

    - 預設只顯示待審核（PENDING）照片
    - 可透過 status 參數篩選其他狀態
    - 按上傳時間排序（最舊優先）
    """
    photos, total = await PhotoModerationService.get_pending_photos(
        db=db,
        page=page,
        page_size=page_size,
        status=status
    )

    return PendingPhotosListResponse(
        photos=[PendingPhotoResponse(**photo) for photo in photos],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=PhotoStatsResponse)
async def get_photo_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得照片審核統計

    返回：
    - 總照片數
    - 待審核數
    - 已通過數
    - 已拒絕數
    - 今日新增待審核數
    - 今日已審核數
    """
    stats = await PhotoModerationService.get_stats(db)
    return PhotoStatsResponse(**stats)


@router.get("/{photo_id}")
async def get_photo_detail(
    photo_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得照片詳情

    返回照片的完整資訊，包含審核歷史。
    """
    try:
        photo_uuid = uuid.UUID(photo_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的照片 ID 格式"
        )

    photo_detail = await PhotoModerationService.get_photo_detail(db, photo_uuid)

    if not photo_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="照片不存在"
        )

    return photo_detail


@router.post("/{photo_id}/review", response_model=PhotoReviewResponse)
async def review_photo(
    photo_id: str,
    request: PhotoReviewRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    審核照片

    - APPROVED: 通過審核
    - REJECTED: 拒絕（需提供原因，會扣除用戶信任分數）
    """
    try:
        photo_uuid = uuid.UUID(photo_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的照片 ID 格式"
        )

    # 驗證拒絕時必須提供原因
    if request.status == "REJECTED" and not request.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="拒絕照片時必須提供原因"
        )

    success, message = await PhotoModerationService.review_photo(
        db=db,
        photo_id=photo_uuid,
        admin_id=current_admin.id,
        status=request.status,
        rejection_reason=request.rejection_reason
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PhotoReviewResponse(
        success=True,
        message=message,
        photo_id=photo_id,
        status=request.status
    )
