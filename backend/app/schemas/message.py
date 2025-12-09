"""訊息相關 Schema"""
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional, List


class MessageResponse(BaseModel):
    """訊息回應"""
    id: UUID4
    match_id: UUID4
    sender_id: UUID4
    content: str
    message_type: str
    is_read: Optional[datetime] = None
    sent_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """聊天記錄回應"""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class MatchWithLastMessageResponse(BaseModel):
    """配對與最後一條訊息"""
    match_id: UUID4
    other_user_id: UUID4
    other_user_name: str
    other_user_avatar: Optional[str] = None
    last_message: Optional[MessageResponse] = None
    unread_count: int
    matched_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """發送訊息請求

    訊息長度限制：1-2000 字符
    即時聊天訊息不宜過長，防止濫用和 DoS 攻擊
    """
    match_id: UUID4
    content: str = Field(..., min_length=1, max_length=2000)
    message_type: str = Field(default="TEXT", pattern="^(TEXT|IMAGE|GIF)$")


class MarkAsReadRequest(BaseModel):
    """標記為已讀請求"""
    message_ids: List[UUID4] = Field(..., min_items=1)
