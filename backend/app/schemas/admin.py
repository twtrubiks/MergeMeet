"""管理後台相關 Schemas"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional


class DashboardStatsResponse(BaseModel):
    """管理後台統計數據"""
    model_config = ConfigDict(from_attributes=True)

    total_users: int
    active_users: int
    banned_users: int
    total_matches: int
    active_matches: int
    total_messages: int
    total_reports: int
    pending_reports: int
    total_blocked_users: int


class ReportDetailResponse(BaseModel):
    """舉報詳情"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporter_id: str
    reporter_email: str
    reported_user_id: str
    reported_user_email: str
    report_type: str
    reason: str
    evidence: Optional[str]
    status: str
    admin_notes: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]


class ReviewReportRequest(BaseModel):
    """處理舉報請求"""
    status: str  # APPROVED, REJECTED, UNDER_REVIEW
    admin_notes: Optional[str] = Field(None, max_length=1000, description="管理員備註（最多 1000 字）")
    action: Optional[str] = None  # BAN_USER, WARNING, NO_ACTION


class UserManagementResponse(BaseModel):
    """用戶管理響應"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    is_active: bool
    is_admin: bool
    trust_score: int
    warning_count: int
    ban_reason: Optional[str]
    banned_until: Optional[datetime]
    created_at: datetime
    email_verified: bool

    @field_validator('trust_score', mode='before')
    @classmethod
    def default_trust_score(cls, v):
        """處理資料庫中的 NULL，使用模型定義的默認值 50"""
        return v if v is not None else 50

    @field_validator('warning_count', mode='before')
    @classmethod
    def default_warning_count(cls, v):
        """處理資料庫中的 NULL，使用模型定義的默認值 0"""
        return v if v is not None else 0


class BanUserRequest(BaseModel):
    """封禁用戶請求"""
    user_id: str
    reason: str = Field(..., min_length=10, max_length=500, description="封禁原因（10-500 字）")
    duration_days: Optional[int] = None  # None = 永久封禁


class UnbanUserRequest(BaseModel):
    """解封用戶請求"""
    user_id: str
