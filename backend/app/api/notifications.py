"""通知 API - 持久化通知管理"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    SuccessResponse,
)

router = APIRouter(prefix="/api/notifications", tags=["通知"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    unread_only: bool = Query(default=False, description="只取未讀"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得通知列表（分頁）"""
    # 基礎查詢
    query = select(Notification).where(Notification.user_id == current_user.id)

    # 只取未讀
    if unread_only:
        query = query.where(Notification.is_read == False)  # noqa: E712

    # 排序（最新優先）
    query = query.order_by(Notification.created_at.desc())

    # 取得總數
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分頁
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    # 取得未讀數量
    unread_query = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False  # noqa: E712
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar() or 0

    return NotificationListResponse(
        notifications=[
            NotificationResponse.model_validate(n) for n in notifications
        ],
        total=total,
        unread_count=unread_count
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得未讀通知數量"""
    query = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False  # noqa: E712
    )
    result = await db.execute(query)
    count = result.scalar() or 0

    return UnreadCountResponse(unread_count=count)


@router.put("/{notification_id}/read", response_model=SuccessResponse)
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """標記單個通知為已讀"""
    # 查詢通知
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在"
        )

    # 標記為已讀
    notification.is_read = True
    await db.commit()

    return SuccessResponse(success=True)


@router.put("/read-all", response_model=SuccessResponse)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """標記全部通知為已讀"""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.commit()

    return SuccessResponse(success=True)


@router.delete("/{notification_id}", response_model=SuccessResponse)
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """刪除單個通知"""
    # 查詢通知
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在"
        )

    # 刪除
    await db.delete(notification)
    await db.commit()

    return SuccessResponse(success=True)
