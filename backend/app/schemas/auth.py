"""認證相關的 Pydantic Schemas"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import date, datetime
from typing import Optional
import re


class RegisterRequest(BaseModel):
    """註冊請求"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "password": "Password123",
            "date_of_birth": "1995-01-01"
        }
    })

    email: EmailStr = Field(..., description="Email 地址")
    password: str = Field(..., min_length=8, max_length=50, description="密碼（至少 8 個字元）")
    date_of_birth: date = Field(..., description="出生日期（用於年齡驗證）")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """驗證密碼強度

        要求:
        - 至少 8 個字元（已在 Field 定義）
        - 至少包含一個大寫字母
        - 至少包含一個小寫字母
        - 至少包含一個數字
        - 不能是常見弱密碼
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("密碼必須包含至少一個大寫字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密碼必須包含至少一個小寫字母")
        if not re.search(r"\d", v):
            raise ValueError("密碼必須包含至少一個數字")

        # 檢查常見弱密碼（最嚴重的弱密碼）
        weak_passwords = [
            '12345678', 'password', 'qwerty123',
            '11111111', '88888888',
            'admin123', '1q2w3e4r'
        ]
        if v.lower() in weak_passwords:
            raise ValueError("密碼太常見，請使用更強的密碼")

        return v


class LoginRequest(BaseModel):
    """登入請求"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "password": "Password123"
        }
    })

    email: EmailStr = Field(..., description="Email 地址")
    password: str = Field(..., description="密碼")


class TokenResponse(BaseModel):
    """Token 回應"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 900
        }
    })

    access_token: str = Field(..., description="存取 Token（JWT）")
    refresh_token: str = Field(..., description="刷新 Token（JWT）")
    token_type: str = Field(default="bearer", description="Token 類型")
    expires_in: int = Field(..., description="過期時間（秒）")


class RefreshTokenRequest(BaseModel):
    """刷新 Token 請求

    refresh_token 為可選：
    - Web 前端：從 HttpOnly Cookie 讀取（發送空 body 或不發送 body）
    - API 客戶端/移動端：從 request body 提供
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    })

    refresh_token: Optional[str] = Field(None, description="刷新 Token（可選，Web 前端從 Cookie 讀取）")


class UserResponse(BaseModel):
    """用戶回應"""
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "email_verified": False,
            "is_active": True,
            "is_admin": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
    })

    id: str = Field(..., description="用戶 ID")
    email: str = Field(..., description="Email 地址")
    email_verified: bool = Field(..., description="Email 是否已驗證")
    is_active: bool = Field(..., description="帳號是否啟用")
    is_admin: bool = Field(..., description="是否為管理員")
    created_at: datetime = Field(..., description="建立時間")


class EmailVerificationRequest(BaseModel):
    """Email 驗證請求"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "verification_code": "123456"
        }
    })

    email: EmailStr = Field(..., description="Email 地址")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6 位數驗證碼")


class ResendVerificationRequest(BaseModel):
    """重新發送驗證碼請求"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com"
        }
    })

    email: EmailStr = Field(..., description="Email 地址")


class ForgotPasswordRequest(BaseModel):
    """忘記密碼請求"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com"
        }
    })

    email: EmailStr = Field(..., description="註冊時使用的 Email")


class ResetPasswordRequest(BaseModel):
    """重置密碼請求"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "abc123def456...",
            "new_password": "NewPassword123"
        }
    })

    token: str = Field(..., description="密碼重置 Token")
    new_password: str = Field(..., min_length=8, max_length=50, description="新密碼（至少 8 個字元）")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """驗證密碼強度（複用 RegisterRequest 的邏輯）"""
        if not re.search(r"[A-Z]", v):
            raise ValueError("密碼必須包含至少一個大寫字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密碼必須包含至少一個小寫字母")
        if not re.search(r"\d", v):
            raise ValueError("密碼必須包含至少一個數字")

        # 檢查常見弱密碼
        weak_passwords = [
            '12345678', 'password', 'qwerty123',
            '11111111', '88888888', 'admin123', '1q2w3e4r'
        ]
        if v.lower() in weak_passwords:
            raise ValueError("密碼太常見，請使用更強的密碼")

        return v


class VerifyResetTokenResponse(BaseModel):
    """驗證重置 Token 回應"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "valid": True,
            "email": "us***r@example.com"
        }
    })

    valid: bool = Field(..., description="Token 是否有效")
    email: Optional[str] = Field(None, description="關聯的遮罩 Email（僅當 valid=True 時返回，格式: us***r@example.com）")


class ChangePasswordRequest(BaseModel):
    """修改密碼請求"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "current_password": "OldPassword123",
            "new_password": "NewPassword456"
        }
    })

    current_password: str = Field(..., min_length=1, description="當前密碼")
    new_password: str = Field(..., min_length=8, max_length=50, description="新密碼（至少 8 個字元）")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """驗證新密碼強度（複用 RegisterRequest 的邏輯）"""
        if not re.search(r"[A-Z]", v):
            raise ValueError("密碼必須包含至少一個大寫字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密碼必須包含至少一個小寫字母")
        if not re.search(r"\d", v):
            raise ValueError("密碼必須包含至少一個數字")

        # 檢查常見弱密碼
        weak_passwords = [
            '12345678', 'password', 'qwerty123',
            '11111111', '88888888', 'admin123', '1q2w3e4r'
        ]
        if v.lower() in weak_passwords:
            raise ValueError("密碼太常見，請使用更強的密碼")

        return v


class ChangePasswordResponse(BaseModel):
    """修改密碼回應"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "密碼修改成功，請重新登入",
            "tokens_invalidated": True
        }
    })

    message: str = Field(..., description="結果訊息")
    tokens_invalidated: bool = Field(..., description="是否已使所有 Token 失效")
