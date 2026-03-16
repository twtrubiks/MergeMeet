"""管理後台相關 Schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    evidence: str | None
    status: str
    admin_notes: str | None
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None


class ReviewReportRequest(BaseModel):
    """處理舉報請求"""

    status: str  # APPROVED, REJECTED, UNDER_REVIEW
    admin_notes: str | None = Field(None, max_length=1000, description="管理員備註（最多 1000 字）")
    action: str | None = None  # BAN_USER, WARNING, NO_ACTION


class UserManagementResponse(BaseModel):
    """用戶管理響應"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    is_active: bool
    is_admin: bool
    trust_score: int
    warning_count: int
    ban_reason: str | None
    banned_until: datetime | None
    created_at: datetime
    email_verified: bool

    @field_validator("trust_score", mode="before")
    @classmethod
    def default_trust_score(cls, v):
        """處理資料庫中的 NULL，使用模型定義的默認值 50"""
        return v if v is not None else 50

    @field_validator("warning_count", mode="before")
    @classmethod
    def default_warning_count(cls, v):
        """處理資料庫中的 NULL，使用模型定義的默認值 0"""
        return v if v is not None else 0


class ReviewReportResponse(BaseModel):
    """處理舉報回應"""

    success: bool
    message: str
    report_id: str
    status: str


class BanUserResponse(BaseModel):
    """封禁用戶回應"""

    success: bool
    message: str
    user_id: str
    banned_until: str


class UnbanUserResponse(BaseModel):
    """解封用戶回應"""

    success: bool
    message: str
    user_id: str


class BanUserRequest(BaseModel):
    """封禁用戶請求"""

    user_id: str
    reason: str = Field(..., min_length=10, max_length=500, description="封禁原因（10-500 字）")
    duration_days: int | None = None  # None = 永久封禁


class UnbanUserRequest(BaseModel):
    """解封用戶請求"""

    user_id: str
