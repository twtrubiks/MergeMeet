"""聊天訊息 REST API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.match import Match, Message
from app.models.profile import Profile
from app.schemas.message import (
    ChatHistoryResponse,
    MessageResponse,
    MatchWithLastMessageResponse,
    MarkAsReadRequest
)

router = APIRouter(prefix="/api/messages")
logger = logging.getLogger(__name__)


@router.get("/matches/{match_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    match_id: str,
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(50, ge=1, le=100, description="每頁訊息數"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得配對的聊天記錄

    - 分頁載入訊息
    - 按時間倒序排列 (最新的在前)
    - 只有配對的成員可以查看
    """
    # 驗證配對是否存在且用戶是成員
    result = await db.execute(
        select(Match).where(
            and_(
                Match.id == match_id,
                Match.status == "ACTIVE",
                or_(
                    Match.user1_id == current_user.id,
                    Match.user2_id == current_user.id
                )
            )
        )
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配對不存在或您無權查看"
        )

    # 計算總訊息數
    count_result = await db.execute(
        select(func.count(Message.id)).where(
            and_(
                Message.match_id == match_id,
                Message.deleted_at.is_(None)
            )
        )
    )
    total = count_result.scalar()

    # 分頁查詢訊息
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Message)
        .where(
            and_(
                Message.match_id == match_id,
                Message.deleted_at.is_(None)
            )
        )
        .order_by(desc(Message.sent_at))
        .offset(offset)
        .limit(page_size)
    )
    messages = result.scalars().all()

    has_more = total > (page * page_size)

    return ChatHistoryResponse(
        messages=[MessageResponse.model_validate(msg) for msg in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/conversations", response_model=List[MatchWithLastMessageResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有對話列表

    - 顯示所有活躍的配對
    - 包含最後一條訊息
    - 顯示未讀訊息數量
    - 按最後訊息時間排序

    優化：批次載入資料，避免 N+1 查詢問題
    """
    # 查詢用戶的所有活躍配對
    result = await db.execute(
        select(Match)
        .where(
            and_(
                Match.status == "ACTIVE",
                or_(
                    Match.user1_id == current_user.id,
                    Match.user2_id == current_user.id
                )
            )
        )
        .order_by(desc(Match.matched_at))
    )
    matches = result.scalars().all()

    if not matches:
        return []

    # 批次載入：收集所有需要的 ID
    match_ids = [match.id for match in matches]
    other_user_ids = [
        match.user2_id if match.user1_id == current_user.id else match.user1_id
        for match in matches
    ]

    # 批次查詢 1：所有對方的個人資料（1 次查詢取代 N 次）
    profiles_result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(Profile.user_id.in_(other_user_ids))
    )
    profiles_by_user_id = {p.user_id: p for p in profiles_result.scalars().all()}

    # 批次查詢 2：所有訊息（用於找最後一條訊息）
    messages_result = await db.execute(
        select(Message)
        .where(
            and_(
                Message.match_id.in_(match_ids),
                Message.deleted_at.is_(None)
            )
        )
        .order_by(Message.match_id, desc(Message.sent_at))
    )
    all_messages = messages_result.scalars().all()

    # 整理每個 match 的最後一條訊息
    last_messages_by_match = {}
    for msg in all_messages:
        if msg.match_id not in last_messages_by_match:
            last_messages_by_match[msg.match_id] = msg

    # 批次查詢 3：所有未讀訊息數（1 次查詢取代 N 次）
    unread_counts_result = await db.execute(
        select(
            Message.match_id,
            func.count(Message.id).label('count')
        )
        .where(
            and_(
                Message.match_id.in_(match_ids),
                Message.sender_id.in_(other_user_ids),
                Message.is_read.is_(None),
                Message.deleted_at.is_(None)
            )
        )
        .group_by(Message.match_id)
    )
    unread_counts_by_match = {row.match_id: row.count for row in unread_counts_result.all()}

    conversations = []

    for match in matches:
        # 確定對方用戶 ID
        other_user_id = match.user2_id if match.user1_id == current_user.id else match.user1_id

        # 從批次載入的數據中獲取
        other_profile = profiles_by_user_id.get(other_user_id)
        last_message = last_messages_by_match.get(match.id)
        unread_count = unread_counts_by_match.get(match.id, 0)

        # 獲取對方的頭像
        other_user_avatar = None
        if other_profile and other_profile.photos:
            profile_photo = next((p for p in other_profile.photos if p.is_profile_picture), None)
            if profile_photo:
                other_user_avatar = profile_photo.url
            elif other_profile.photos:
                other_user_avatar = other_profile.photos[0].url

        conversations.append(
            MatchWithLastMessageResponse(
                match_id=match.id,
                other_user_id=other_user_id,
                other_user_name=other_profile.display_name if other_profile else "Unknown",
                other_user_avatar=other_user_avatar,
                last_message=MessageResponse.model_validate(last_message) if last_message else None,
                unread_count=unread_count,
                matched_at=match.matched_at
            )
        )

    # 按最後訊息時間排序 (有訊息的在前)
    conversations.sort(
        key=lambda x: x.last_message.sent_at if x.last_message else x.matched_at,
        reverse=True
    )

    return conversations


@router.post("/messages/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_messages_as_read(
    request: MarkAsReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    標記訊息為已讀

    - 批量標記多條訊息
    - 只能標記發送給自己的訊息
    """
    # 查詢訊息並驗證權限
    result = await db.execute(
        select(Message)
        .where(
            and_(
                Message.id.in_(request.message_ids),
                Message.deleted_at.is_(None)
            )
        )
    )
    messages = result.scalars().all()

    # 獲取這些訊息所屬的配對
    match_ids = list(set([msg.match_id for msg in messages]))
    matches_result = await db.execute(
        select(Match)
        .where(
            and_(
                Match.id.in_(match_ids),
                Match.status == "ACTIVE",
                or_(
                    Match.user1_id == current_user.id,
                    Match.user2_id == current_user.id
                )
            )
        )
    )
    user_matches = {m.id for m in matches_result.scalars().all()}

    # 更新訊息狀態
    updated_count = 0

    for message in messages:
        # 驗證：訊息必須屬於用戶的配對，且不是自己發送的
        if message.match_id in user_matches and message.sender_id != current_user.id:
            if not message.is_read:
                message.is_read = func.now()
                updated_count += 1

    if updated_count > 0:
        await db.commit()

    return None


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除訊息 (軟刪除)

    - 只有發送者可以刪除自己的訊息
    - 使用軟刪除，不實際從資料庫移除
    - 通過 WebSocket 即時通知配對中的另一方
    """
    from app.websocket.manager import manager

    # 查詢訊息
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="訊息不存在"
        )

    # 驗證是否為發送者
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您只能刪除自己的訊息"
        )

    # 保存 match_id 用於 WebSocket 廣播
    match_id = str(message.match_id)

    # 軟刪除 (帶異常處理確保事務完整性)
    try:
        message.deleted_at = func.now()
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete message {message_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="訊息刪除失敗，請稍後再試"
        )

    # 通過 WebSocket 通知配對中的另一方
    await manager.send_to_match(
        match_id,
        {
            "type": "message_deleted",
            "message_id": message_id,
            "match_id": match_id,
            "deleted_by": str(current_user.id)
        },
        exclude_user=str(current_user.id)  # 排除刪除者本人
    )

    return None
