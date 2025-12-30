"""聊天訊息 REST API"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from typing import List
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
    MarkAsReadRequest,
    ChatImageUploadResponse
)
from app.websocket.manager import manager
from app.services.file_storage import file_storage
from app.core.config import settings

router = APIRouter(prefix="/api/messages")
logger = logging.getLogger(__name__)


@router.get("/matches/{match_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    match_id: str,
    before_id: str = Query(None, description="Cursor: 載入比此訊息 ID 更早的訊息"),
    limit: int = Query(50, ge=1, le=100, description="每次載入訊息數"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得配對的聊天記錄 (Cursor-based pagination)

    - 初次載入：不傳 before_id，取最新 N 條訊息
    - 載入更多：傳入 before_id，取比該訊息更早的 N 條
    - 訊息按時間正序返回（舊的在前，新的在後）
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

    # 構建查詢條件
    conditions = [
        Message.match_id == match_id,
        Message.deleted_at.is_(None)
    ]

    # 如果有 cursor，添加 before 條件
    if before_id:
        # 先查詢 cursor 訊息的 sent_at
        cursor_result = await db.execute(
            select(Message.sent_at).where(Message.id == before_id)
        )
        cursor_sent_at = cursor_result.scalar_one_or_none()

        if cursor_sent_at:
            # 取比 cursor 更早的訊息
            # 使用 (sent_at, id) 組合條件處理相同時間的訊息
            conditions.append(
                or_(
                    Message.sent_at < cursor_sent_at,
                    and_(
                        Message.sent_at == cursor_sent_at,
                        Message.id < before_id
                    )
                )
            )

    # 查詢訊息：倒序取 limit+1 條（多取一條判斷 has_more）
    result = await db.execute(
        select(Message)
        .where(and_(*conditions))
        .order_by(desc(Message.sent_at), desc(Message.id))
        .limit(limit + 1)
    )
    messages = result.scalars().all()

    # 判斷是否有更多
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]  # 移除多取的一條

    # 反轉為正序（舊的在前，前端期望的格式）
    messages = list(reversed(messages))

    # 計算 next_cursor（本次結果中最舊訊息的 ID，供下次查詢使用）
    next_cursor = messages[0].id if messages and has_more else None

    return ChatHistoryResponse(
        messages=[MessageResponse.model_validate(msg) for msg in messages],
        has_more=has_more,
        next_cursor=next_cursor,
        total=total
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


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
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


@router.post("/matches/{match_id}/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_messages_as_read(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    標記該對話中所有未讀訊息為已讀

    當用戶進入聊天室時調用此 API，確保所有未讀訊息（包括因分頁未載入的舊訊息）
    都被正確標記為已讀。

    - 只標記對方發送給自己的訊息
    - 冪等操作：重複調用不會有副作用
    """
    # 驗證用戶屬於該配對
    match_result = await db.execute(
        select(Match)
        .where(
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
    match = match_result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配對不存在或您無權操作"
        )

    # 1. 先查詢待標記的訊息（取得 id 和 sender_id，用於發送 WebSocket 通知）
    unread_result = await db.execute(
        select(Message.id, Message.sender_id)
        .where(
            and_(
                Message.match_id == match_id,
                Message.sender_id != current_user.id,  # 對方發送的
                Message.is_read.is_(None),  # 未讀
                Message.deleted_at.is_(None)  # 未刪除
            )
        )
    )
    unread_messages = unread_result.all()

    # 2. 批量更新所有未讀訊息
    read_time = datetime.now(timezone.utc)
    if unread_messages:
        await db.execute(
            Message.__table__.update()
            .where(
                and_(
                    Message.match_id == match_id,
                    Message.sender_id != current_user.id,
                    Message.is_read.is_(None),
                    Message.deleted_at.is_(None)
                )
            )
            .values(is_read=read_time)
        )
        await db.commit()

        # 3. 發送 WebSocket 通知給發送者（讓發送者即時看到已讀狀態）
        for msg_id, sender_id in unread_messages:
            await manager.send_personal_message(
                str(sender_id),
                {
                    "type": "read_receipt",
                    "message_id": str(msg_id),
                    "read_by": str(current_user.id),
                    "read_at": read_time.isoformat()
                }
            )

        logger.info(
            f"Marked {len(unread_messages)} messages as read in match {match_id} "
            f"and sent WebSocket notifications"
        )

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


@router.post("/matches/{match_id}/upload-image", response_model=ChatImageUploadResponse)
async def upload_chat_image(
    match_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上傳聊天圖片

    - 支援 JPEG, PNG, GIF, WebP 格式
    - 最大檔案大小: 5MB
    - 只有配對成員可以上傳
    - 返回圖片和縮圖 URL
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
            detail="配對不存在或您無權上傳"
        )

    # 驗證 MIME 類型
    content_type = file.content_type
    if content_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支援的圖片格式，僅支援 JPEG, PNG, GIF, WebP"
        )

    # 讀取檔案內容（流式讀取防止 DoS）
    file_content = b""
    chunk_size = 64 * 1024  # 64KB
    max_size = settings.MAX_UPLOAD_SIZE

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_content += chunk
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"檔案過大，最大允許 {max_size // 1024 // 1024}MB"
            )

    if len(file_content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="檔案不能為空"
        )

    # 儲存圖片
    try:
        (
            image_id, image_url, thumbnail_url, width, height, is_gif
        ) = await file_storage.save_chat_image(
            match_id=match_id,
            user_id=str(current_user.id),
            file_content=file_content,
            filename=file.filename or "image",
            content_type=content_type
        )
    except Exception as e:
        logger.error(f"Failed to save chat image: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="圖片儲存失敗，請稍後再試"
        )

    return ChatImageUploadResponse(
        image_id=image_id,
        image_url=image_url,
        thumbnail_url=thumbnail_url,
        width=width,
        height=height,
        is_gif=is_gif
    )
