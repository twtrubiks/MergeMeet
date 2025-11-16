"""WebSocket 連接管理器"""
from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta

from app.core.security import decode_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 連接管理器

    管理所有活躍的 WebSocket 連接，並提供訊息發送功能

    使用 asyncio.Lock 保護並發安全
    """

    def __init__(self):
        # 用戶ID -> WebSocket 連接
        self.active_connections: Dict[str, WebSocket] = {}

        # 配對ID -> 用戶ID列表 (用於聊天室管理)
        self.match_rooms: Dict[str, List[str]] = {}

        # 用戶ID -> 最後心跳時間 (用於檢測異常斷線)
        self.connection_heartbeats: Dict[str, datetime] = {}

        # 並發安全鎖
        self._connections_lock = asyncio.Lock()
        self._rooms_lock = asyncio.Lock()

        # 定期清理任務
        self._cleanup_task: Optional[asyncio.Task] = None

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

        # 檢查 Token 類型（必須是 access token）
        if payload.get("type") != "access":
            await websocket.close(code=1008, reason="Invalid token type")
            logger.warning(f"WebSocket connection with wrong token type for user {user_id}")
            return False

        # 明確檢查 Token 過期時間（雙重保險）
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            await websocket.close(code=1008, reason="Token expired")
            logger.warning(f"WebSocket connection with expired token for user {user_id}")
            return False

        # 接受連接
        await websocket.accept()

        # 並發安全：使用鎖保護字典操作
        async with self._connections_lock:
            self.active_connections[user_id] = websocket
            # 初始化心跳時間（防止異常斷線）
            self.connection_heartbeats[user_id] = datetime.now(timezone.utc)
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
        # 並發安全：使用鎖保護字典操作
        async with self._connections_lock:
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].close()
                except Exception as e:
                    logger.error(f"Error closing connection for user {user_id}: {e}")

                del self.active_connections[user_id]
                # 清除心跳時間
                self.connection_heartbeats.pop(user_id, None)
                logger.info(f"User {user_id} disconnected")

        # 從所有配對房間移除
        async with self._rooms_lock:
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

    async def join_match_room(self, match_id: str, user_id: str):
        """加入配對聊天室

        Args:
            match_id: 配對 ID
            user_id: 用戶 ID
        """
        # 並發安全：使用鎖保護字典操作
        async with self._rooms_lock:
            if match_id not in self.match_rooms:
                self.match_rooms[match_id] = []
            if user_id not in self.match_rooms[match_id]:
                self.match_rooms[match_id].append(user_id)
                logger.info(f"User {user_id} joined match room {match_id}")

    async def leave_match_room(self, match_id: str, user_id: str):
        """離開配對聊天室

        Args:
            match_id: 配對 ID
            user_id: 用戶 ID
        """
        # 並發安全：使用鎖保護字典操作
        async with self._rooms_lock:
            if match_id in self.match_rooms and user_id in self.match_rooms[match_id]:
                self.match_rooms[match_id].remove(user_id)
                if not self.match_rooms[match_id]:
                    del self.match_rooms[match_id]
                logger.info(f"User {user_id} left match room {match_id}")

    async def is_online(self, user_id: str) -> bool:
        """檢查用戶是否在線

        Args:
            user_id: 用戶 ID

        Returns:
            bool: 是否在線
        """
        # 並發安全：讀取時也使用鎖
        async with self._connections_lock:
            return user_id in self.active_connections

    async def get_online_users(self) -> List[str]:
        """獲取所有在線用戶

        Returns:
            List[str]: 在線用戶 ID 列表
        """
        # 並發安全：讀取時也使用鎖
        async with self._connections_lock:
            return list(self.active_connections.keys())

    async def start_cleanup_task(self):
        """啟動定期清理任務（清理異常斷線的連接）"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("Started WebSocket cleanup task")

    async def _periodic_cleanup(self):
        """定期清理超時連接（每分鐘執行一次）"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分鐘檢查一次
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}", exc_info=True)

    async def _cleanup_stale_connections(self):
        """清理超過 5 分鐘無心跳的連接

        檢測並移除異常斷線的 WebSocket 連接，防止資源洩漏
        """
        now = datetime.now(timezone.utc)
        stale_users = []

        # 找出所有過期的連接（使用鎖保護）
        async with self._connections_lock:
            for user_id, last_heartbeat in self.connection_heartbeats.items():
                if now - last_heartbeat > timedelta(minutes=5):
                    stale_users.append(user_id)

        # 斷開過期連接
        for user_id in stale_users:
            logger.warning(f"Cleaning up stale connection for user {user_id}")
            await self.disconnect(user_id)

        if stale_users:
            logger.info(f"Cleaned up {len(stale_users)} stale connections")

    async def update_heartbeat(self, user_id: str):
        """更新心跳時間（由 WebSocket 端點定期調用）

        Args:
            user_id: 用戶 ID
        """
        if user_id in self.connection_heartbeats:
            self.connection_heartbeats[user_id] = datetime.now(timezone.utc)


# 全局單例實例
manager = ConnectionManager()
