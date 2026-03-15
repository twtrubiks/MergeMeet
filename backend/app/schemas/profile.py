"""個人檔案相關的 Pydantic Schemas"""

import uuid as uuid_module
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class GenderEnum(str, Enum):  # noqa: UP042
    """性別枚舉"""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class GenderPreferenceEnum(str, Enum):  # noqa: UP042
    """性別偏好枚舉"""

    MALE = "male"
    FEMALE = "female"
    BOTH = "both"
    ALL = "all"


class LocationRequest(BaseModel):
    """地理位置請求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"latitude": 25.0330, "longitude": 121.5654, "location_name": "台北市"}
        }
    )

    latitude: float = Field(..., ge=-90, le=90, description="緯度")
    longitude: float = Field(..., ge=-180, le=180, description="經度")
    location_name: str | None = Field(None, max_length=255, description="地點名稱")


class ProfileCreateRequest(BaseModel):
    """建立個人檔案請求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "display_name": "小明",
                "gender": "male",
                "bio": "喜歡旅遊和美食",
                "location": {"latitude": 25.0330, "longitude": 121.5654, "location_name": "台北市"},
            }
        }
    )

    display_name: str = Field(..., min_length=1, max_length=100, description="顯示名稱")
    gender: GenderEnum = Field(..., description="性別")
    bio: str | None = Field(None, max_length=500, description="自我介紹")
    location: LocationRequest | None = Field(None, description="地理位置")


class ProfileUpdateRequest(BaseModel):
    """更新個人檔案請求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "display_name": "小明",
                "bio": "喜歡旅遊、美食和運動",
                "min_age_preference": 25,
                "max_age_preference": 35,
                "max_distance_km": 50,
                "gender_preference": "female",
            }
        }
    )

    display_name: str | None = Field(None, min_length=1, max_length=100, description="顯示名稱")
    gender: GenderEnum | None = Field(None, description="性別")
    bio: str | None = Field(None, max_length=500, description="自我介紹")
    location: LocationRequest | None = Field(None, description="地理位置")
    min_age_preference: int | None = Field(None, ge=18, le=99, description="最小年齡偏好")
    max_age_preference: int | None = Field(None, ge=18, le=99, description="最大年齡偏好")
    max_distance_km: int | None = Field(None, ge=1, le=500, description="最大距離（公里）")
    gender_preference: GenderPreferenceEnum | None = Field(None, description="性別偏好")

    @field_validator("max_age_preference")
    @classmethod
    def validate_age_range(cls, v: int | None, info: ValidationInfo) -> int | None:
        """驗證年齡範圍"""
        if (
            info.data.get("min_age_preference") is not None
            and v is not None
            and v < info.data["min_age_preference"]
        ):
            raise ValueError("最大年齡必須大於或等於最小年齡")
        return v


class PhotoModerationStatusEnum(str, Enum):  # noqa: UP042
    """照片審核狀態枚舉"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PhotoResponse(BaseModel):
    """照片回應"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="照片 ID")
    url: str = Field(..., description="照片 URL")
    thumbnail_url: str | None = Field(None, description="縮圖 URL")
    display_order: int = Field(..., description="顯示順序")
    is_profile_picture: bool = Field(..., description="是否為頭像")
    moderation_status: str = Field(..., description="審核狀態")
    rejection_reason: str | None = Field(None, description="拒絕原因")
    created_at: datetime = Field(..., description="建立時間")


class InterestTagResponse(BaseModel):
    """興趣標籤回應"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="標籤 ID")
    name: str = Field(..., description="標籤名稱")
    category: str = Field(..., description="標籤分類")
    icon: str | None = Field(None, description="圖示")


class ProfileResponse(BaseModel):
    """個人檔案回應"""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "display_name": "小明",
                "gender": "male",
                "bio": "喜歡旅遊和美食",
                "location_name": "台北市",
                "age": 28,
                "min_age_preference": 25,
                "max_age_preference": 35,
                "max_distance_km": 50,
                "gender_preference": "female",
                "is_complete": True,
                "is_visible": True,
                "photos": [],
                "interests": [],
                "created_at": "2024-01-01T00:00:00Z",
            }
        },
    )

    id: str = Field(..., description="檔案 ID")
    user_id: str = Field(..., description="用戶 ID")
    display_name: str = Field(..., description="顯示名稱")
    gender: str | None = Field(None, description="性別")
    bio: str | None = Field(None, description="自我介紹")
    location_name: str | None = Field(None, description="地點名稱")
    age: int | None = Field(None, description="年齡")

    # 偏好設定
    min_age_preference: int = Field(..., description="最小年齡偏好")
    max_age_preference: int = Field(..., description="最大年齡偏好")
    max_distance_km: int = Field(..., description="最大距離（公里）")
    gender_preference: str | None = Field(None, description="性別偏好")

    # 狀態
    is_complete: bool = Field(..., description="檔案是否完整")
    is_visible: bool = Field(..., description="檔案是否可見")

    # 照片和興趣
    photos: list[PhotoResponse] = Field(default=[], description="照片列表")
    interests: list[InterestTagResponse] = Field(default=[], description="興趣標籤")

    created_at: datetime = Field(..., description="建立時間")
    updated_at: datetime | None = Field(None, description="更新時間")


class InterestTagCreateRequest(BaseModel):
    """建立興趣標籤請求"""

    model_config = ConfigDict(
        json_schema_extra={"example": {"name": "籃球", "category": "sports", "icon": "🏀"}}
    )

    name: str = Field(..., min_length=1, max_length=50, description="標籤名稱")
    category: str = Field(..., min_length=1, max_length=50, description="標籤分類")
    icon: str | None = Field(None, max_length=10, description="圖示（emoji）")


class UpdateInterestsRequest(BaseModel):
    """更新興趣標籤請求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "interest_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440002",
                ]
            }
        }
    )

    interest_ids: list[str] = Field(
        ..., min_length=3, max_length=10, description="興趣標籤 ID 列表（3-10個）"
    )

    @field_validator("interest_ids")
    @classmethod
    def validate_uuid_list(cls, v: list[str]) -> list[str]:
        """驗證每個 ID 都是有效的 UUID 格式"""
        for id_str in v:
            if id_str is None:
                raise ValueError("標籤 ID 不能為空")
            try:
                uuid_module.UUID(id_str)
            except (ValueError, TypeError) as e:
                raise ValueError(f"無效的標籤 ID 格式: {id_str}") from e
        return v


class PhotoOrderRequest(BaseModel):
    """照片順序調整請求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "photo_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440002",
                ]
            }
        }
    )

    photo_ids: list[str] = Field(
        ..., min_length=1, max_length=6, description="照片 ID 陣列，按新順序排列"
    )
