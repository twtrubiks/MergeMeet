"""WebSocket API 端點"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime
import json
import logging
import uuid

from app.core.database import get_db
from app.websocket.manager import manager
from app.models.match import Message, Match
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token"),
    user_id: str = Query(..., description="用戶 ID")
):
    """
    WebSocket 連接端點

    用於建立即時聊天連接，支援:
    - 聊天訊息發送/接收
    - 打字狀態指示器
    - 訊息已讀回條
    - 加入/離開配對聊天室

    Query Parameters:
        - token: JWT access token
        - user_id: 當前用戶的 ID
    """
    # 轉換 user_id 為 UUID 類型
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.error(f"Invalid user_id format: {user_id}")
        await websocket.close(code=1008, reason="Invalid user_id format")
        return

    # 建立連接
    connected = await manager.connect(websocket, user_id, token)
    if not connected:
        return

    try:
        while True:
            # 接收訊息
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # 處理不同類型的訊息
            message_type = message_data.get("type")

            if message_type == "chat_message":
                await handle_chat_message(message_data, user_uuid)

            elif message_type == "typing":
                await handle_typing_indicator(message_data, user_id)

            elif message_type == "read_receipt":
                await handle_read_receipt(message_data, user_id)

            elif message_type == "join_match":
                await handle_join_match(message_data, user_id)

            elif message_type == "leave_match":
                await handle_leave_match(message_data, user_id)

            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        await manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)
        await manager.disconnect(user_id)


async def handle_chat_message(data: dict, sender_id: uuid.UUID):
    """處理聊天訊息

    Args:
        data: 訊息資料，包含 match_id 和 content
        sender_id: 發送者 ID (UUID 類型)
    """
    from app.core.database import AsyncSessionLocal
    from app.services.content_moderation import ContentModerationService

    async with AsyncSessionLocal() as db:
        try:
            match_id = data.get("match_id")
            content = data.get("content", "").strip()

            if not match_id or not content:
                logger.warning(f"Invalid message data from {sender_id}: {data}")
                return

            # 內容審核：檢查敏感詞
            is_approved, violations, action = await ContentModerationService.check_message_content(
                content, db, sender_id
            )
            if not is_approved:
                logger.warning(f"Unsafe content detected from {sender_id}: {violations}")
                await manager.send_personal_message(
                    str(sender_id),
                    {
                        "type": "error",
                        "message": "訊息包含不當內容，已被系統拒絕",
                        "violations": violations
                    }
                )

                # 記錄違規行為（可選：增加警告次數）
                result = await db.execute(
                    select(User).where(User.id == sender_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    user.warning_count += 1
                    await db.commit()
                    logger.info(f"User {sender_id} warning count increased to {user.warning_count}")

                return

            # 驗證配對是否存在且為活躍狀態
            result = await db.execute(
                select(Match).where(
                    and_(
                        Match.id == match_id,
                        Match.status == "ACTIVE"
                    )
                )
            )
            match = result.scalar_one_or_none()

            if not match:
                logger.warning(f"Match {match_id} not found or inactive")
                await manager.send_personal_message(
                    str(sender_id),
                    {
                        "type": "error",
                        "message": "配對不存在或已取消"
                    }
                )
                return

            # 驗證發送者是否為配對的成員
            if sender_id not in [match.user1_id, match.user2_id]:
                logger.warning(f"User {sender_id} not in match {match_id}")
                await manager.send_personal_message(
                    str(sender_id),
                    {
                        "type": "error",
                        "message": "您不是這個配對的成員"
                    }
                )
                return

            # 儲存訊息到資料庫
            message = Message(
                match_id=match_id,
                sender_id=sender_id,
                content=content,
                message_type=data.get("message_type", "TEXT")
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)

            # 準備要發送的訊息資料
            message_payload = {
                "type": "new_message",
                "message": {
                    "id": str(message.id),
                    "match_id": str(message.match_id),
                    "sender_id": str(message.sender_id),
                    "content": message.content,
                    "message_type": message.message_type,
                    "sent_at": message.sent_at.isoformat(),
                    "is_read": message.is_read.isoformat() if message.is_read else None
                }
            }

            # 發送給配對的所有用戶 (包括發送者自己，用於確認)
            await manager.send_to_match(match_id, message_payload)

            logger.info(f"Message {message.id} sent in match {match_id}")

        except Exception as e:
            logger.error(f"Error handling chat message: {e}", exc_info=True)
            await manager.send_personal_message(
                str(sender_id),
                {
                    "type": "error",
                    "message": "訊息發送失敗"
                }
            )


async def handle_typing_indicator(data: dict, user_id: str):
    """處理打字指示器

    Args:
        data: 包含 match_id 和 is_typing 的資料
        user_id: 正在打字的用戶 ID
    """
    match_id = data.get("match_id")
    is_typing = data.get("is_typing", False)

    if not match_id:
        return

    # 發送打字狀態給配對中的其他用戶
    await manager.send_to_match(
        match_id,
        {
            "type": "typing",
            "user_id": user_id,
            "is_typing": is_typing,
            "match_id": match_id
        },
        exclude_user=user_id
    )


async def handle_read_receipt(data: dict, user_id: str):
    """處理訊息已讀回條

    Args:
        data: 包含 message_id 的資料
        user_id: 讀取訊息的用戶 ID
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            message_id = data.get("message_id")

            if not message_id:
                return

            # 查詢訊息
            result = await db.execute(
                select(Message).where(Message.id == message_id)
            )
            message = result.scalar_one_or_none()

            if not message:
                logger.warning(f"Message {message_id} not found")
                return

            # 只有接收者才能標記訊息為已讀
            if str(message.sender_id) == user_id:
                return

            # 更新訊息狀態
            if not message.is_read:
                message.is_read = func.now()
                await db.commit()

                # 通知發送者
                await manager.send_personal_message(
                    str(message.sender_id),
                    {
                        "type": "read_receipt",
                        "message_id": str(message.id),
                        "read_by": user_id,
                        "read_at": message.is_read.isoformat()
                    }
                )

                logger.info(f"Message {message_id} marked as read by {user_id}")

        except Exception as e:
            logger.error(f"Error handling read receipt: {e}", exc_info=True)


async def handle_join_match(data: dict, user_id: str):
    """處理加入配對聊天室

    Args:
        data: 包含 match_id 的資料
        user_id: 要加入的用戶 ID
    """
    match_id = data.get("match_id")

    if not match_id:
        return

    manager.join_match_room(match_id, user_id)

    # 通知用戶已加入聊天室
    await manager.send_personal_message(
        user_id,
        {
            "type": "joined_match",
            "match_id": match_id
        }
    )


async def handle_leave_match(data: dict, user_id: str):
    """處理離開配對聊天室

    Args:
        data: 包含 match_id 的資料
        user_id: 要離開的用戶 ID
    """
    match_id = data.get("match_id")

    if not match_id:
        return

    manager.leave_match_room(match_id, user_id)

    logger.info(f"User {user_id} left match {match_id}")
