"""WebSocket API 端點

安全性改進：使用首次訊息認證機制，Token 不再透過 Query Parameter 傳遞。

認證流程：
1. 客戶端建立 WebSocket 連接（無需 Query Parameters）
2. 連接成功後立即發送認證訊息：{"type": "auth", "token": "...", "user_id": "..."}
3. 伺服器驗證 Token 並標記連接為已認證
4. 認證成功後才允許其他操作
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, and_
from datetime import datetime, timezone
import json
import logging
import uuid
import asyncio

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.websocket.manager import manager
from app.models.match import Message, Match
from app.models.user import User
from app.models.profile import Profile
from app.services.content_moderation import ContentModerationService

logger = logging.getLogger(__name__)
router = APIRouter()


def validate_uuid(value: str, field_name: str = "ID") -> uuid.UUID | None:
    """驗證字串是否為有效的 UUID 格式

    Args:
        value: 要驗證的字串
        field_name: 欄位名稱（用於日誌記錄）

    Returns:
        有效的 UUID 對象，或 None（如果無效）
    """
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid {field_name} format: {value}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 連接端點（首次訊息認證機制）

    安全認證流程：
    1. 客戶端建立連接（無 Query Parameters，Token 不暴露在 URL）
    2. 伺服器接受連接並等待認證訊息（5 秒超時）
    3. 客戶端發送：{"type": "auth", "token": "JWT...", "user_id": "uuid"}
    4. 伺服器驗證 Token 並建立連接
    5. 認證成功後才允許其他操作

    支援功能：
    - 聊天訊息發送/接收
    - 打字狀態指示器
    - 訊息已讀回條
    - 加入/離開配對聊天室
    - 心跳 ping/pong
    """
    # 接受連接（但尚未認證）
    await websocket.accept()

    user_id = None

    try:
        # 等待首次認證訊息（5 秒超時）
        try:
            auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        except asyncio.TimeoutError:
            await websocket.close(code=1008, reason="Authentication timeout")
            logger.warning("WebSocket authentication timeout")
            return

        # 驗證是否為認證訊息
        if auth_data.get("type") != "auth":
            await websocket.close(code=1008, reason="First message must be auth")
            logger.warning(f"WebSocket first message not auth: {auth_data.get('type')}")
            return

        # 提取認證資訊
        token = auth_data.get("token")
        user_id_str = auth_data.get("user_id")

        if not token or not user_id_str:
            await websocket.close(code=1008, reason="Missing token or user_id")
            logger.warning("WebSocket auth missing credentials")
            return

        # 驗證 user_id 格式
        user_uuid = validate_uuid(user_id_str, "user_id")
        if not user_uuid:
            await websocket.close(code=1008, reason="Invalid user_id format")
            return

        user_id = user_id_str

        # 建立連接並驗證 Token（連接已接受，傳入 already_accepted=True）
        connected = await manager.connect(websocket, user_id, token, already_accepted=True)
        if not connected:
            return

        # 發送認證成功回應
        await websocket.send_json({
            "type": "auth_success",
            "message": "Authentication successful",
            "user_id": user_id
        })
        logger.info(f"WebSocket authenticated successfully for user {user_id}")

        # 進入訊息處理循環
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

            elif message_type == "pong":
                # 心跳回應：更新用戶的心跳時間
                await manager.update_heartbeat(user_id)
                logger.debug(f"Received pong from user {user_id}")

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
    async with AsyncSessionLocal() as db:
        try:
            match_id_str = data.get("match_id")
            content = data.get("content", "").strip()
            message_type = data.get("message_type", "TEXT").upper()

            # 驗證訊息類型
            if message_type not in ("TEXT", "IMAGE", "GIF"):
                message_type = "TEXT"

            # 驗證 match_id 格式
            match_id = validate_uuid(match_id_str, "match_id")
            if not match_id or not content:
                logger.warning(f"Invalid message data from {sender_id}: {data}")
                await manager.send_personal_message(
                    str(sender_id),
                    {
                        "type": "error",
                        "message": "無效的配對 ID 或訊息內容"
                    }
                )
                return

            # 對於圖片/GIF 訊息，驗證 content 是有效 JSON
            if message_type in ("IMAGE", "GIF"):
                try:
                    image_data = json.loads(content)
                    # 檢查必要欄位
                    if not image_data.get("image_url") or not image_data.get("thumbnail_url"):
                        raise ValueError("Missing required fields")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Invalid image message format from {sender_id}: {e}")
                    await manager.send_personal_message(
                        str(sender_id),
                        {
                            "type": "error",
                            "message": "無效的圖片訊息格式"
                        }
                    )
                    return
            else:
                # 只對文字訊息執行以下驗證

                # 驗證訊息長度（防止 DoS 攻擊）
                # 即時聊天訊息建議限制在 2000 字符以內
                if len(content) > settings.MAX_MESSAGE_LENGTH:
                    await manager.send_personal_message(
                        str(sender_id),
                        {
                            "type": "error",
                            "message": f"訊息過長，最多 {settings.MAX_MESSAGE_LENGTH} 字符"
                        }
                    )
                    logger.warning(f"Message too long from {sender_id}: {len(content)} chars")
                    return

                # 內容審核：檢查敏感詞
                (
                    is_approved, violations, action
                ) = await ContentModerationService.check_message_content(
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
                    try:
                        result = await db.execute(
                            select(User).where(User.id == sender_id)
                        )
                        user = result.scalar_one_or_none()
                        if user:
                            user.warning_count += 1
                            await db.commit()
                            logger.info(
                                f"User {sender_id} warning count increased to "
                                f"{user.warning_count}"
                            )
                    except Exception as e:
                        await db.rollback()
                        logger.error(f"Failed to update warning count: {e}")

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

            # 儲存訊息到資料庫（確保事務完整性）
            try:
                message = Message(
                    match_id=match_id,
                    sender_id=sender_id,
                    content=content,
                    message_type=message_type
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

                logger.info(f"Preparing to send message {message.id} to match {match_id}")
                logger.debug(f"Message payload: {message_payload}")

                # 發送給配對的所有用戶 (包括發送者自己，用於確認)
                # 注意：match_rooms 的 key 是字符串，需要轉換
                await manager.send_to_match(str(match_id), message_payload)

                logger.info(f"Message {message.id} sent in match {match_id}")

                # ========== 即時通知功能 ==========
                # 實作三種通知類型之三：
                # 3. notification_message - 新訊息通知（接收者不在聊天室時）
                # ========================================

                # 確定接收者（對方）的 user_id
                receiver_id = match.user2_id if match.user1_id == sender_id else match.user1_id
                receiver_id_str = str(receiver_id)

                # 檢查接收者是否在這個聊天室中
                # 如果接收者不在聊天室，發送通知提醒
                match_id_str_key = str(match_id)
                users_in_room = manager.match_rooms.get(match_id_str_key, [])

                if receiver_id_str not in users_in_room:
                    # 查詢發送者的 Profile 資訊（用於通知顯示名稱）
                    sender_profile_result = await db.execute(
                        select(Profile).where(Profile.user_id == sender_id)
                    )
                    sender_profile = sender_profile_result.scalar_one_or_none()
                    sender_name = sender_profile.display_name if sender_profile else "用戶"

                    # 準備訊息預覽（根據訊息類型）
                    if message_type == "IMAGE":
                        preview = "[圖片]"
                    elif message_type == "GIF":
                        preview = "[GIF]"
                    else:
                        # 文字訊息：截取前 50 字
                        preview = content[:50] + "..." if len(content) > 50 else content

                    # 【通知類型 3】新訊息通知 (notification_message)
                    await manager.send_personal_message(
                        receiver_id_str,
                        {
                            "type": "notification_message",
                            "match_id": str(match_id),
                            "sender_id": str(sender_id),
                            "sender_name": sender_name,
                            "preview": preview,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    logger.info(
                        f"Sent notification_message to user {receiver_id_str} "
                        f"(not in chat room)"
                    )

            except Exception as e:
                # 事務失敗，回滾並通知用戶
                await db.rollback()
                logger.error(f"Database error while saving message: {e}", exc_info=True)
                raise  # 重新拋出異常，由外層處理

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
    match_id_str = data.get("match_id")
    is_typing = data.get("is_typing", False)

    # 驗證 match_id 格式
    match_id = validate_uuid(match_id_str, "match_id")
    if not match_id:
        return

    # 發送打字狀態給配對中的其他用戶
    await manager.send_to_match(
        str(match_id),
        {
            "type": "typing",
            "user_id": user_id,
            "is_typing": is_typing,
            "match_id": str(match_id)
        },
        exclude_user=user_id
    )


async def handle_read_receipt(data: dict, user_id: str):
    """處理訊息已讀回條

    Args:
        data: 包含 message_id 的資料
        user_id: 讀取訊息的用戶 ID
    """
    async with AsyncSessionLocal() as db:
        try:
            message_id_str = data.get("message_id")

            # 驗證 message_id 格式
            message_id = validate_uuid(message_id_str, "message_id")
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

            # 標記為已讀（如果尚未標記）
            if not message.is_read:
                read_time = datetime.now(timezone.utc)
                message.is_read = read_time
                await db.commit()

                # 通知發送者（只用 WebSocket，避免與 REST API 重複）
                await manager.send_personal_message(
                    str(message.sender_id),
                    {
                        "type": "read_receipt",
                        "message_id": str(message.id),
                        "read_by": user_id,
                        "read_at": read_time.isoformat()
                    }
                )

                logger.info(f"Message {message_id} marked as read by {user_id} via WebSocket")
            else:
                logger.debug(f"Message {message_id} already marked as read, skipping")

        except Exception as e:
            logger.error(f"Error handling read receipt: {e}", exc_info=True)


async def handle_join_match(data: dict, user_id: str):
    """處理加入配對聊天室

    Args:
        data: 包含 match_id 的資料
        user_id: 要加入的用戶 ID
    """
    match_id_str = data.get("match_id")

    # 驗證 match_id 格式
    match_id = validate_uuid(match_id_str, "match_id")
    if not match_id:
        return

    await manager.join_match_room(str(match_id), user_id)

    # 通知用戶已加入聊天室
    await manager.send_personal_message(
        user_id,
        {
            "type": "joined_match",
            "match_id": str(match_id)
        }
    )


async def handle_leave_match(data: dict, user_id: str):
    """處理離開配對聊天室

    Args:
        data: 包含 match_id 的資料
        user_id: 要離開的用戶 ID
    """
    match_id_str = data.get("match_id")

    # 驗證 match_id 格式
    match_id = validate_uuid(match_id_str, "match_id")
    if not match_id:
        return

    await manager.leave_match_room(str(match_id), user_id)

    logger.info(f"User {user_id} left match {match_id}")
