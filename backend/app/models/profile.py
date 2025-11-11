"""個人檔案相關資料模型"""
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, DateTime, Table
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Profile(Base):
    """個人檔案模型"""
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # 基本資訊
    display_name = Column(String(100), nullable=False)
    gender = Column(String(20))  # male, female, non_binary, prefer_not_to_say
    bio = Column(Text)

    # 地理位置 (PostGIS)
    location = Column(Geography(geometry_type='POINT', srid=4326))
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
    photos = relationship("Photo", back_populates="profile", cascade="all, delete-orphan", order_by="Photo.display_order")
    interests = relationship("InterestTag", secondary="profile_interests", back_populates="profiles")

    def __repr__(self):
        return f"<Profile {self.display_name}>"


class Photo(Base):
    """照片模型"""
    __tablename__ = "photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    display_order = Column(Integer, default=0)
    is_profile_picture = Column(Boolean, default=False)

    # 元資料
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    mime_type = Column(String(50))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 關聯
    profile = relationship("Profile", back_populates="photos")

    def __repr__(self):
        return f"<Photo {self.id}>"


class InterestTag(Base):
    """興趣標籤模型"""
    __tablename__ = "interest_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # sports, music, food, travel, etc.
    icon = Column(String(10))  # emoji icon
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 關聯
    profiles = relationship("Profile", secondary="profile_interests", back_populates="interests")

    def __repr__(self):
        return f"<InterestTag {self.name}>"


# 多對多關聯表：Profile <-> InterestTag
profile_interests = Table(
    'profile_interests',
    Base.metadata,
    Column('profile_id', UUID(as_uuid=True), ForeignKey('profiles.id', ondelete="CASCADE"), primary_key=True),
    Column('interest_id', UUID(as_uuid=True), ForeignKey('interest_tags.id', ondelete="CASCADE"), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)
