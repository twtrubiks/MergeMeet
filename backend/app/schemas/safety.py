"""安全功能相關 Schema"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
import uuid as uuid_module


class BlockUserRequest(BaseModel):
    """封鎖用戶請求"""
    reason: Optional[str] = Field(None, max_length=500, description="封鎖原因")


class UnblockUserRequest(BaseModel):
    """解除封鎖請求"""


class BlockedUserResponse(BaseModel):
    """封鎖用戶回應"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    blocked_user_id: str
    blocked_user_email: str
    reason: Optional[str]
    created_at: datetime


class ReportUserRequest(BaseModel):
    """舉報用戶請求"""
    reported_user_id: str = Field(..., description="被舉報用戶 ID")
    report_type: str = Field(..., description="舉報類型")
    reason: str = Field(..., min_length=10, max_length=1000, description="舉報原因")
    evidence: Optional[str] = Field(None, max_length=2000, description="證據說明")

    @field_validator('reported_user_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """驗證 UUID 格式"""
        if v is None:
            raise ValueError("用戶 ID 不能為空")
        try:
            uuid_module.UUID(v)
        except (ValueError, TypeError):
            raise ValueError("無效的用戶 ID 格式")
        return v


class ReportResponse(BaseModel):
    """舉報回應"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    reported_user_id: str
    report_type: str
    reason: str
    status: str
    created_at: datetime
