"""管理後台相關 Schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class DashboardStatsResponse(BaseModel):
    """管理後台統計數據"""
    total_users: int
    active_users: int
    banned_users: int
    total_matches: int
    active_matches: int
    total_messages: int
    total_reports: int
    pending_reports: int
    total_blocked_users: int

    class Config:
        from_attributes = True


class ReportDetailResponse(BaseModel):
    """舉報詳情"""
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

    class Config:
        from_attributes = True


class ReviewReportRequest(BaseModel):
    """處理舉報請求"""
    status: str  # APPROVED, REJECTED, UNDER_REVIEW
    admin_notes: Optional[str] = Field(None, max_length=1000, description="管理員備註（最多 1000 字）")
    action: Optional[str] = None  # BAN_USER, WARNING, NO_ACTION


class UserManagementResponse(BaseModel):
    """用戶管理響應"""
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

    class Config:
        from_attributes = True


class BanUserRequest(BaseModel):
    """封禁用戶請求"""
    user_id: str
    reason: str = Field(..., min_length=10, max_length=500, description="封禁原因（10-500 字）")
    duration_days: Optional[int] = None  # None = 永久封禁


class UnbanUserRequest(BaseModel):
    """解封用戶請求"""
    user_id: str
