"""通知相關 Schema"""
from pydantic import BaseModel, ConfigDict, Field, UUID4
from datetime import datetime
from typing import Optional, List, Dict, Any


class NotificationResponse(BaseModel):
    """單個通知回應"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    type: str = Field(..., description="通知類型: notification_message/match/liked")
    title: str
    content: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """通知列表回應"""
    notifications: List[NotificationResponse]
    total: int = Field(..., description="總通知數")
    unread_count: int = Field(..., description="未讀通知數")


class UnreadCountResponse(BaseModel):
    """未讀數量回應"""
    unread_count: int


class SuccessResponse(BaseModel):
    """操作成功回應"""
    success: bool = True
