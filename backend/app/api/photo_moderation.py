"""照片審核 API

管理員用於審核用戶上傳的照片。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.schemas.photo_moderation import (
    PendingPhotoResponse,
    PendingPhotosListResponse,
    PhotoDetailResponse,
    PhotoReviewRequest,
    PhotoReviewResponse,
    PhotoStatsResponse,
)
from app.services.photo_moderation import PhotoModerationService

router = APIRouter()


@router.get("/pending", response_model=PendingPhotosListResponse)
async def get_pending_photos(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=100, description="每頁數量"),
    status: str | None = Query(
        None, pattern="^(PENDING|APPROVED|REJECTED)$", description="篩選狀態"
    ),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    取得待審核照片列表

    - 預設只顯示待審核（PENDING）照片
    - 可透過 status 參數篩選其他狀態
    - 按上傳時間排序（最舊優先）
    """
    photos, total = await PhotoModerationService.get_pending_photos(
        db=db, page=page, page_size=page_size, status=status
    )

    return PendingPhotosListResponse(
        photos=[PendingPhotoResponse(**photo) for photo in photos],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=PhotoStatsResponse)
async def get_photo_stats(
    current_admin: User = Depends(get_current_admin_user), db: AsyncSession = Depends(get_db)
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


@router.get("/{photo_id}", response_model=PhotoDetailResponse)
async def get_photo_detail(
    photo_id: UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    取得照片詳情

    返回照片的完整資訊，包含審核歷史。
    """
    # FastAPI 自動驗證 UUID 格式，無效的 UUID 會返回 422 錯誤
    photo_detail = await PhotoModerationService.get_photo_detail(db, photo_id)

    if not photo_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")

    return photo_detail


@router.post("/{photo_id}/review", response_model=PhotoReviewResponse)
async def review_photo(
    photo_id: UUID,
    request: PhotoReviewRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    審核照片

    - APPROVED: 通過審核
    - REJECTED: 拒絕（需提供原因，會扣除用戶信任分數）
    """
    # FastAPI 自動驗證 UUID 格式，無效的 UUID 會返回 422 錯誤

    # 驗證拒絕時必須提供原因
    if request.status == "REJECTED" and not request.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="拒絕照片時必須提供原因"
        )

    success, message = await PhotoModerationService.review_photo(
        db=db,
        photo_id=photo_id,
        admin_id=current_admin.id,
        status=request.status,
        rejection_reason=request.rejection_reason,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return PhotoReviewResponse(
        success=True, message=message, photo_id=str(photo_id), status=request.status
    )
