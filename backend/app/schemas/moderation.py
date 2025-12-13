"""內容審核相關 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ============ Sensitive Word Schemas ============

class SensitiveWordCreate(BaseModel):
    """創建敏感詞請求"""
    word: str = Field(..., min_length=1, max_length=100, description="敏感詞")
    category: str = Field(
        ...,
        description="分類: SEXUAL, SCAM, HARASSMENT, VIOLENCE, "
                    "PERSONAL_INFO, OTHER"
    )
    severity: str = Field("MEDIUM", description="嚴重程度: LOW, MEDIUM, HIGH, CRITICAL")
    action: str = Field("WARN", description="處理動作: WARN, REJECT, AUTO_BAN")
    is_regex: bool = Field(False, description="是否為正則表達式")
    description: Optional[str] = Field(None, max_length=500, description="描述說明")


class SensitiveWordUpdate(BaseModel):
    """更新敏感詞請求"""
    category: Optional[str] = None
    severity: Optional[str] = None
    action: Optional[str] = None
    is_regex: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SensitiveWordResponse(BaseModel):
    """敏感詞回應"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    word: str
    category: str
    severity: str
    action: str
    is_regex: bool
    description: Optional[str]
    is_active: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: Optional[datetime]


class SensitiveWordListResponse(BaseModel):
    """敏感詞列表回應"""
    words: List[SensitiveWordResponse]
    total: int


# ============ Content Appeal Schemas ============

class ContentAppealCreate(BaseModel):
    """創建內容申訴請求"""
    appeal_type: str = Field(..., description="申訴類型: MESSAGE, PROFILE, PHOTO")
    rejected_content: str = Field(..., description="被拒絕的內容")
    violations: str = Field(..., description="觸發的違規項目（JSON）")
    reason: str = Field(..., min_length=20, max_length=1000, description="申訴理由")


class ContentAppealReview(BaseModel):
    """審核申訴請求（管理員）"""
    status: str = Field(..., description="審核結果: APPROVED, REJECTED")
    admin_response: str = Field(..., min_length=10, max_length=500, description="管理員回覆")


class ContentAppealResponse(BaseModel):
    """申訴回應"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    appeal_type: str
    rejected_content: str
    violations: str
    reason: str
    status: str
    admin_response: Optional[str]
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime


class ContentAppealListResponse(BaseModel):
    """申訴列表回應"""
    appeals: List[ContentAppealResponse]
    total: int


# ============ Moderation Log Schemas ============

class ModerationLogCreate(BaseModel):
    """創建審核日誌請求"""
    user_id: str
    content_type: str
    original_content: str
    is_approved: bool
    violations: Optional[str] = None
    triggered_word_ids: Optional[str] = None
    action_taken: str


class ModerationLogResponse(BaseModel):
    """審核日誌回應"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    content_type: str
    original_content: str
    is_approved: bool
    violations: Optional[str]
    triggered_word_ids: Optional[str]
    action_taken: str
    created_at: datetime


class ModerationLogListResponse(BaseModel):
    """審核日誌列表回應"""
    logs: List[ModerationLogResponse]
    total: int


# ============ Moderation Statistics Schemas ============

class ModerationStatsResponse(BaseModel):
    """審核統計回應"""
    total_sensitive_words: int
    active_sensitive_words: int
    total_appeals: int
    pending_appeals: int
    approved_appeals: int
    rejected_appeals: int
    total_violations_today: int
    total_violations_this_week: int
    total_violations_this_month: int
    most_triggered_words: List[dict]  # [{word: str, count: int}]
