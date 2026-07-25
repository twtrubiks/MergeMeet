"""個人檔案相關資料模型"""

import uuid

from geoalchemy2 import Geography
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Profile(Base):
    """個人檔案模型"""

    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # 基本資訊
    display_name = Column(String(100), nullable=False)
    gender = Column(String(20))  # male, female, non_binary, prefer_not_to_say
    bio = Column(Text)

    # 地理位置 (PostGIS)
    location = Column(Geography(geometry_type="POINT", srid=4326))
    location_name = Column(String(255))

    # 搜尋偏好
    min_age_preference = Column(Integer, default=18)
    max_age_preference = Column(Integer, default=99)
    max_distance_km = Column(Integer, default=50)
    gender_preference = Column(String(20), nullable=True)  # male, female, both, all

    # 狀態
    is_complete = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    last_active = Column(DateTime(timezone=True))

    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 關聯
    user = relationship("User", back_populates="profile")
    photos = relationship(
        "Photo",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Photo.display_order",
    )
    interests = relationship(
        "InterestTag", secondary="profile_interests", back_populates="profiles"
    )

    @property
    def public_photos(self) -> list["Photo"]:
        """公開可見的照片（排除審核駁回），依 display_order 排序

        巡邏制審核語意：PENDING 照片先上架、事後審核，REJECTED 立即下架。
        所有對其他用戶輸出照片的地方（探索、配對、對話頭像）都必須使用此屬性。
        """
        return sorted(
            (photo for photo in self.photos if photo.moderation_status != "REJECTED"),
            key=lambda photo: photo.display_order,
        )

    def reassign_primary_photo(self) -> None:
        """將主頭像指到第一張未被駁回的照片；無合格照片時清除所有主頭像標記"""
        for photo in self.photos:
            photo.is_profile_picture = False
        candidates = self.public_photos
        if candidates:
            candidates[0].is_profile_picture = True

    def __repr__(self):
        return f"<Profile {self.display_name}>"


def check_profile_completeness(profile: Profile) -> bool:
    """
    檢查個人檔案完整度

    完整的檔案需要：
    - 基本資料：顯示名稱、性別、自我介紹
    - 至少 1 張未被駁回的照片
    - 3-10 個興趣標籤
    """
    has_basic_info = bool(profile.display_name and profile.gender and profile.bio)
    has_photos = len(profile.public_photos) >= 1
    has_interests = 3 <= len(profile.interests) <= 10

    return has_basic_info and has_photos and has_interests


class Photo(Base):
    """照片模型"""

    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    display_order = Column(Integer, default=0)
    is_profile_picture = Column(Boolean, default=False)

    # 元資料
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    mime_type = Column(String(50))

    # 審核相關欄位
    moderation_status = Column(
        String(20), default="PENDING", nullable=False, index=True
    )  # PENDING, APPROVED, REJECTED
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # 自動審核結果（目前由人工審核流程留白，僅在管理後台照片詳情回傳）
    auto_moderation_score = Column(Integer, nullable=True)  # 0-100
    auto_moderation_labels = Column(Text, nullable=True)  # JSON 格式

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 關聯
    profile = relationship("Profile", back_populates="photos")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<Photo {self.id}>"


class InterestTag(Base):
    """興趣標籤模型"""

    __tablename__ = "interest_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    # sports, music, food, travel, etc.
    category = Column(String(50), nullable=False, index=True)
    icon = Column(String(10))  # emoji icon
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 關聯
    profiles = relationship("Profile", secondary="profile_interests", back_populates="interests")

    def __repr__(self):
        return f"<InterestTag {self.name}>"


# 多對多關聯表：Profile <-> InterestTag
profile_interests = Table(
    "profile_interests",
    Base.metadata,
    Column(
        "profile_id",
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "interest_id",
        UUID(as_uuid=True),
        ForeignKey("interest_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)
