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
from app.models.notification import Notification
from app.services.content_moderation import ContentModerationService
from app.services.trust_score import TrustScoreService
from app.services.redis_client import redis_client

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


# ========== handle_chat_message 輔助函數 ==========


async def _send_error(sender_id: uuid.UUID, message: str) -> None:
    """發送錯誤訊息給用戶"""
    await manager.send_personal_message(
        str(sender_id),
        {"type": "error", "message": message}
    )


def _validate_chat_input(
    data: dict, sender_id: uuid.UUID
) -> tuple[bool, str | None, dict | None]:
    """驗證聊天訊息輸入

    Args:
        data: 訊息資料
        sender_id: 發送者 ID

    Returns:
        (is_valid, error_message, parsed_data)
        parsed_data 包含: match_id (UUID), content (str), message_type (str)
    """
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
        return False, "無效的配對 ID 或訊息內容", None

    return True, None, {
        "match_id": match_id,
        "content": content,
        "message_type": message_type
    }


def _validate_image_content(content: str, sender_id: uuid.UUID) -> tuple[bool, str | None]:
    """驗證圖片/GIF 訊息格式

    Args:
        content: 訊息內容（應為 JSON 字串）
        sender_id: 發送者 ID

    Returns:
        (is_valid, error_message)
    """
    try:
        image_data = json.loads(content)
        if not image_data.get("image_url") or not image_data.get("thumbnail_url"):
            raise ValueError("Missing required fields")
        return True, None
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Invalid image message format from {sender_id}: {e}")
        return False, "無效的圖片訊息格式"


async def _validate_text_content(
    content: str,
    sender_id: uuid.UUID,
    db
) -> tuple[bool, str | None, list | None]:
    """驗證文字訊息（長度和內容審核）

    Args:
        content: 訊息內容
        sender_id: 發送者 ID
        db: 資料庫 session

    Returns:
        (is_valid, error_message, violations)
    """
    # 驗證訊息長度
    if len(content) > settings.MAX_MESSAGE_LENGTH:
        logger.warning(f"Message too long from {sender_id}: {len(content)} chars")
        return False, f"訊息過長，最多 {settings.MAX_MESSAGE_LENGTH} 字符", None

    # 內容審核
    is_approved, violations, _ = await ContentModerationService.check_message_content(
        content, db, sender_id
    )
    if not is_approved:
        logger.warning(f"Unsafe content detected from {sender_id}: {violations}")
        return False, "訊息包含不當內容，已被系統拒絕", violations

    return True, None, None


async def _validate_match_access(
    match_id: uuid.UUID,
    sender_id: uuid.UUID,
    db
) -> tuple[bool, str | None, Match | None]:
    """驗證配對存在且發送者是成員

    Args:
        match_id: 配對 ID
        sender_id: 發送者 ID
        db: 資料庫 session

    Returns:
        (is_valid, error_message, match_object)
    """
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
        return False, "配對不存在或已取消", None

    if sender_id not in [match.user1_id, match.user2_id]:
        logger.warning(f"User {sender_id} not in match {match_id}")
        return False, "您不是這個配對的成員", None

    return True, None, match


async def _record_content_violation(sender_id: uuid.UUID, db) -> None:
    """記錄用戶內容違規"""
    try:
        result = await db.execute(
            select(User).where(User.id == sender_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.warning_count += 1
            await db.commit()
            logger.info(
                f"User {sender_id} warning count increased to {user.warning_count}"
            )

            # 信任分數減分：內容違規 -3 分
            await TrustScoreService.adjust_score(db, sender_id, "content_violation")
            logger.info(f"Trust score -3 for user {sender_id} (content_violation)")
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update warning count: {e}")


async def _check_message_rate_limit(
    sender_id: uuid.UUID, db
) -> tuple[bool, str | None]:
    """檢查低信任用戶的訊息發送限制

    Args:
        sender_id: 發送者 ID
        db: 資料庫 session

    Returns:
        (can_send, error_message): 是否可發送，錯誤訊息
    """
    try:
        # 獲取用戶信任分數
        result = await db.execute(
            select(User.trust_score).where(User.id == sender_id)
        )
        trust_score = result.scalar_one_or_none()

        if trust_score is None:
            return True, None  # 用戶不存在，跳過限制

        # 正常用戶無限制
        if trust_score >= TrustScoreService.RESTRICTION_THRESHOLD:
            return True, None

        # 低信任用戶檢查限制
        redis = await redis_client.get_connection()
        can_send, remaining = await TrustScoreService.check_message_rate_limit(
            sender_id, trust_score, redis
        )

        if not can_send:
            return False, (
                f"訊息發送限制：您今日已達上限 "
                f"({TrustScoreService.LOW_TRUST_MESSAGE_LIMIT} 則)"
            )

        # 記錄訊息發送
        await TrustScoreService.record_message_sent(sender_id, redis)
        logger.info(
            f"Low trust user {sender_id} sent message, "
            f"remaining: {remaining - 1}"
        )
        return True, None

    except Exception as e:
        logger.error(f"Error checking message rate limit: {e}")
        return True, None  # 出錯時不阻擋發送


async def _save_and_broadcast_message(
    match: Match,
    sender_id: uuid.UUID,
    parsed: dict,
    db
) -> Message:
    """儲存訊息到資料庫並廣播

    Args:
        match: 配對對象
        sender_id: 發送者 ID
        parsed: 解析後的訊息資料
        db: 資料庫 session

    Returns:
        儲存的 Message 對象
    """
    message = Message(
        match_id=parsed["match_id"],
        sender_id=sender_id,
        content=parsed["content"],
        message_type=parsed["message_type"]
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

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

    logger.info(f"Preparing to send message {message.id} to match {parsed['match_id']}")
    logger.debug(f"Message payload: {message_payload}")

    await manager.send_to_match(str(parsed["match_id"]), message_payload)
    logger.info(f"Message {message.id} sent in match {parsed['match_id']}")

    return message


async def _send_message_notification(
    match: Match,
    sender_id: uuid.UUID,
    message: Message,
    db
) -> None:
    """如果接收者不在聊天室，發送通知（含持久化）

    Args:
        match: 配對對象
        sender_id: 發送者 ID
        message: 訊息對象
        db: 資料庫 session
    """
    receiver_id = match.user2_id if match.user1_id == sender_id else match.user1_id
    receiver_id_str = str(receiver_id)
    match_id_str = str(match.id)
    users_in_room = manager.match_rooms.get(match_id_str, [])

    if receiver_id_str in users_in_room:
        return

    # 查詢發送者 Profile
    sender_profile_result = await db.execute(
        select(Profile).where(Profile.user_id == sender_id)
    )
    sender_profile = sender_profile_result.scalar_one_or_none()
    sender_name = sender_profile.display_name if sender_profile else "用戶"

    # 準備訊息預覽
    if message.message_type == "IMAGE":
        preview = "[圖片]"
    elif message.message_type == "GIF":
        preview = "[GIF]"
    else:
        preview = message.content[:50] + "..." if len(message.content) > 50 else message.content

    # 持久化通知到資料庫
    notification = Notification(
        user_id=receiver_id,
        type="notification_message",
        title=f"{sender_name} 傳來新訊息",
        content=preview,
        data={
            "match_id": str(match.id),
            "sender_id": str(sender_id),
            "sender_name": sender_name,
            "message_id": str(message.id)
        }
    )
    db.add(notification)
    await db.commit()
    logger.info(f"Persisted notification_message for user {receiver_id_str}")

    # 發送 WebSocket 通知
    await manager.send_personal_message(
        receiver_id_str,
        {
            "type": "notification_message",
            "match_id": str(match.id),
            "sender_id": str(sender_id),
            "sender_name": sender_name,
            "preview": preview,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    logger.info(f"Sent notification_message to user {receiver_id_str} (not in chat room)")


# ========== websocket_endpoint 輔助函數 ==========


async def _authenticate_websocket(
    websocket: WebSocket
) -> tuple[str | None, uuid.UUID | None]:
    """處理 WebSocket 認證流程

    認證步驟：
    1. 等待認證訊息（5 秒超時）
    2. 驗證訊息類型為 auth
    3. 提取並驗證 token 和 user_id
    4. 通過 manager 驗證 token 有效性

    Args:
        websocket: WebSocket 連接

    Returns:
        (user_id_str, user_uuid) 認證成功
        (None, None) 認證失敗（連接已關閉）
    """
    # 等待首次認證訊息（5 秒超時）
    try:
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
    except asyncio.TimeoutError:
        await websocket.close(code=1008, reason="Authentication timeout")
        logger.warning("WebSocket authentication timeout")
        return None, None

    # 驗證是否為認證訊息
    if auth_data.get("type") != "auth":
        await websocket.close(code=1008, reason="First message must be auth")
        logger.warning(f"WebSocket first message not auth: {auth_data.get('type')}")
        return None, None

    # 提取認證資訊
    token = auth_data.get("token")
    user_id_str = auth_data.get("user_id")

    if not token or not user_id_str:
        await websocket.close(code=1008, reason="Missing token or user_id")
        logger.warning("WebSocket auth missing credentials")
        return None, None

    # 驗證 user_id 格式
    user_uuid = validate_uuid(user_id_str, "user_id")
    if not user_uuid:
        await websocket.close(code=1008, reason="Invalid user_id format")
        return None, None

    # 建立連接並驗證 Token（連接已接受，傳入 already_accepted=True）
    connected = await manager.connect(websocket, user_id_str, token, already_accepted=True)
    if not connected:
        return None, None

    # 發送認證成功回應
    await websocket.send_json({
        "type": "auth_success",
        "message": "Authentication successful",
        "user_id": user_id_str
    })
    logger.info(f"WebSocket authenticated successfully for user {user_id_str}")

    return user_id_str, user_uuid


async def _handle_pong(user_id: str, _user_uuid: uuid.UUID) -> None:
    """處理心跳回應

    Args:
        user_id: 用戶 ID 字串
        _user_uuid: 用戶 UUID（未使用，保持介面一致）
    """
    await manager.update_heartbeat(user_id)
    logger.debug(f"Received pong from user {user_id}")


async def _handle_chat_message_wrapper(user_id: str, user_uuid: uuid.UUID, data: dict) -> None:
    """聊天訊息處理包裝器（統一介面）

    Args:
        user_id: 用戶 ID 字串（未使用）
        user_uuid: 用戶 UUID
        data: 訊息資料
    """
    await handle_chat_message(data, user_uuid)


async def _handle_typing_wrapper(user_id: str, _user_uuid: uuid.UUID, data: dict) -> None:
    """打字指示器處理包裝器"""
    await handle_typing_indicator(data, user_id)


async def _handle_read_receipt_wrapper(user_id: str, _user_uuid: uuid.UUID, data: dict) -> None:
    """已讀回條處理包裝器"""
    await handle_read_receipt(data, user_id)


async def _handle_join_match_wrapper(user_id: str, _user_uuid: uuid.UUID, data: dict) -> None:
    """加入配對處理包裝器"""
    await handle_join_match(data, user_id)


async def _handle_leave_match_wrapper(user_id: str, _user_uuid: uuid.UUID, data: dict) -> None:
    """離開配對處理包裝器"""
    await handle_leave_match(data, user_id)


async def _handle_pong_wrapper(user_id: str, user_uuid: uuid.UUID, _data: dict) -> None:
    """心跳回應處理包裝器"""
    await _handle_pong(user_id, user_uuid)


# 消息類型處理器映射（字典分發模式）
# 注意：這些包裝器在檔案稍後定義，但 Python 在運行時會正確解析
MESSAGE_HANDLERS: dict[str, callable] = {}


def _init_message_handlers() -> None:
    """初始化消息處理器映射（延遲初始化以避免循環引用）"""
    global MESSAGE_HANDLERS
    MESSAGE_HANDLERS = {
        "chat_message": _handle_chat_message_wrapper,
        "typing": _handle_typing_wrapper,
        "read_receipt": _handle_read_receipt_wrapper,
        "join_match": _handle_join_match_wrapper,
        "leave_match": _handle_leave_match_wrapper,
        "pong": _handle_pong_wrapper,
    }


async def _process_messages(
    websocket: WebSocket,
    user_id: str,
    user_uuid: uuid.UUID
) -> None:
    """處理 WebSocket 訊息循環

    使用字典分發模式處理不同類型的訊息。

    Args:
        websocket: WebSocket 連接
        user_id: 用戶 ID 字串
        user_uuid: 用戶 UUID
    """
    # 確保處理器已初始化
    if not MESSAGE_HANDLERS:
        _init_message_handlers()

    while True:
        data = await websocket.receive_text()
        message_data = json.loads(data)
        message_type = message_data.get("type")

        handler = MESSAGE_HANDLERS.get(message_type)
        if handler:
            await handler(user_id, user_uuid, message_data)
        else:
            logger.warning(f"Unknown message type: {message_type}")


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
        # 執行認證流程
        user_id, user_uuid = await _authenticate_websocket(websocket)
        if not user_id:
            return

        # 進入訊息處理循環
        await _process_messages(websocket, user_id, user_uuid)

    except WebSocketDisconnect:
        await manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)
        await manager.disconnect(user_id)


async def handle_chat_message(data: dict, sender_id: uuid.UUID):
    """處理聊天訊息 - 協調器

    Args:
        data: 訊息資料，包含 match_id 和 content
        sender_id: 發送者 ID (UUID 類型)
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. 輸入驗證
            is_valid, error, parsed = _validate_chat_input(data, sender_id)
            if not is_valid:
                await _send_error(sender_id, error)
                return

            # 2. 訊息限制檢查（低信任用戶）
            can_send, rate_error = await _check_message_rate_limit(sender_id, db)
            if not can_send:
                await _send_error(sender_id, rate_error)
                return

            # 3. 內容驗證（根據類型）
            if parsed["message_type"] in ("IMAGE", "GIF"):
                is_valid, error = _validate_image_content(
                    parsed["content"], sender_id
                )
                if not is_valid:
                    await _send_error(sender_id, error)
                    return
            else:
                is_valid, error, violations = await _validate_text_content(
                    parsed["content"], sender_id, db
                )
                if not is_valid:
                    if violations:
                        await _record_content_violation(sender_id, db)
                    await _send_error(sender_id, error)
                    return

            # 4. 配對驗證
            is_valid, error, match = await _validate_match_access(
                parsed["match_id"], sender_id, db
            )
            if not is_valid:
                await _send_error(sender_id, error)
                return

            # 5. 存儲並發送
            message = await _save_and_broadcast_message(
                match, sender_id, parsed, db
            )

            # 6. 離線通知
            await _send_message_notification(match, sender_id, message, db)

        except Exception as e:
            logger.error(f"Error handling chat message: {e}", exc_info=True)
            await _send_error(sender_id, "訊息發送失敗")


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
