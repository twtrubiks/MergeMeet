"""安全功能相關 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BlockUserRequest(BaseModel):
    """封鎖用戶請求"""
    reason: Optional[str] = Field(None, max_length=500, description="封鎖原因")


class UnblockUserRequest(BaseModel):
    """解除封鎖請求"""


class BlockedUserResponse(BaseModel):
    """封鎖用戶回應"""
    id: str
    blocked_user_id: str
    blocked_user_email: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportUserRequest(BaseModel):
    """舉報用戶請求"""
    reported_user_id: str = Field(..., description="被舉報用戶 ID")
    report_type: str = Field(..., description="舉報類型")
    reason: str = Field(..., min_length=10, max_length=1000, description="舉報原因")
    evidence: Optional[str] = Field(None, max_length=2000, description="證據說明")


class ReportResponse(BaseModel):
    """舉報回應"""
    id: str
    reported_user_id: str
    report_type: str
    reason: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
