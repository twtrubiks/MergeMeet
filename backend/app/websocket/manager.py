"""WebSocket 連接管理器"""
from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import logging

from app.core.security import decode_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 連接管理器

    管理所有活躍的 WebSocket 連接，並提供訊息發送功能
    """

    def __init__(self):
        # 用戶ID -> WebSocket 連接
        self.active_connections: Dict[str, WebSocket] = {}

        # 配對ID -> 用戶ID列表 (用於聊天室管理)
        self.match_rooms: Dict[str, List[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, token: str) -> bool:
        """建立 WebSocket 連接

        Args:
            websocket: WebSocket 連接實例
            user_id: 用戶 ID
            token: JWT Token

        Returns:
            bool: 連接是否成功
        """
        # 驗證 Token
        payload = decode_token(token)
        if not payload or payload.get("sub") != user_id:
            await websocket.close(code=1008, reason="Invalid token")
            logger.warning(f"Invalid token for user {user_id}")
            return False

        # 接受連接
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

        # 發送連接成功訊息
        await self.send_personal_message(
            user_id,
            {"type": "connection", "status": "connected", "user_id": user_id}
        )

        return True

    async def disconnect(self, user_id: str):
        """斷開連接

        Args:
            user_id: 用戶 ID
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].close()
            except Exception as e:
                logger.error(f"Error closing connection for user {user_id}: {e}")

            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected")

            # 從所有配對房間移除
            for match_id in list(self.match_rooms.keys()):
                if user_id in self.match_rooms[match_id]:
                    self.match_rooms[match_id].remove(user_id)
                    if not self.match_rooms[match_id]:
                        del self.match_rooms[match_id]

    async def send_personal_message(self, user_id: str, message: dict):
        """發送個人訊息

        Args:
            user_id: 用戶 ID
            message: 訊息內容 (dict)
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                await self.disconnect(user_id)

    async def send_to_match(
        self,
        match_id: str,
        message: dict,
        exclude_user: Optional[str] = None
    ):
        """發送訊息給配對中的所有用戶

        Args:
            match_id: 配對 ID
            message: 訊息內容 (dict)
            exclude_user: 要排除的用戶 ID (通常是發送者)
        """
        if match_id in self.match_rooms:
            for user_id in self.match_rooms[match_id]:
                if user_id != exclude_user:
                    await self.send_personal_message(user_id, message)

    def join_match_room(self, match_id: str, user_id: str):
        """加入配對聊天室

        Args:
            match_id: 配對 ID
            user_id: 用戶 ID
        """
        if match_id not in self.match_rooms:
            self.match_rooms[match_id] = []
        if user_id not in self.match_rooms[match_id]:
            self.match_rooms[match_id].append(user_id)
            logger.info(f"User {user_id} joined match room {match_id}")

    def leave_match_room(self, match_id: str, user_id: str):
        """離開配對聊天室

        Args:
            match_id: 配對 ID
            user_id: 用戶 ID
        """
        if match_id in self.match_rooms and user_id in self.match_rooms[match_id]:
            self.match_rooms[match_id].remove(user_id)
            if not self.match_rooms[match_id]:
                del self.match_rooms[match_id]
            logger.info(f"User {user_id} left match room {match_id}")

    def is_online(self, user_id: str) -> bool:
        """檢查用戶是否在線

        Args:
            user_id: 用戶 ID

        Returns:
            bool: 是否在線
        """
        return user_id in self.active_connections

    def get_online_users(self) -> List[str]:
        """獲取所有在線用戶

        Returns:
            List[str]: 在線用戶 ID 列表
        """
        return list(self.active_connections.keys())


# 全局單例實例
manager = ConnectionManager()
