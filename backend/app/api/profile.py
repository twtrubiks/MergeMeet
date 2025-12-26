"""個人檔案相關 API"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List
from PIL import Image
import uuid
import logging
import io

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.profile import Profile, Photo, InterestTag
from app.schemas.profile import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileResponse,
    PhotoResponse,
    InterestTagResponse,
    InterestTagCreateRequest,
    UpdateInterestsRequest,
    PhotoOrderRequest,
)
from app.services.content_moderation import ContentModerationService
from app.services.file_storage import file_storage

router = APIRouter(prefix="/api/profile")
logger = logging.getLogger(__name__)


def calculate_age(date_of_birth: date) -> int:
    """計算年齡"""
    today = date.today()
    age = relativedelta(today, date_of_birth).years
    return age


def check_profile_completeness(profile: Profile) -> bool:
    """
    檢查個人檔案完整度

    完整的檔案需要：
    - 基本資料：顯示名稱、性別、自我介紹
    - 至少 1 張照片
    - 3-10 個興趣標籤
    """
    has_basic_info = bool(
        profile.display_name and
        profile.gender and
        profile.bio
    )
    has_photos = len(profile.photos) >= 1
    has_interests = 3 <= len(profile.interests) <= 10

    return has_basic_info and has_photos and has_interests


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    request: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    建立個人檔案

    - 一個用戶只能有一個檔案
    - 可選地理位置
    """
    # 檢查是否已有檔案
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    existing_profile = result.scalar_one_or_none()

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="個人檔案已存在"
        )

    # 內容審核：檢查個人簡介
    if request.bio:
        is_approved, violations, action = await ContentModerationService.check_profile_content(
            db=db,
            user_id=current_user.id,
            bio=request.bio
        )
        if not is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "個人簡介包含不當內容",
                    "violations": violations,
                    "action": action
                }
            )

    # 建立檔案
    new_profile = Profile(
        user_id=current_user.id,
        display_name=request.display_name,
        gender=request.gender.value,
        bio=request.bio,
    )

    # 設置地理位置（使用 GeoAlchemy2 函數避免 SQL 注入）
    if request.location:
        new_profile.location = ST_SetSRID(
            ST_MakePoint(request.location.longitude, request.location.latitude),
            4326
        )
        new_profile.location_name = request.location.location_name

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    # 計算年齡
    age = calculate_age(current_user.date_of_birth)

    return ProfileResponse(
        id=str(new_profile.id),
        user_id=str(new_profile.user_id),
        display_name=new_profile.display_name,
        gender=new_profile.gender,
        bio=new_profile.bio,
        location_name=new_profile.location_name,
        age=age,
        min_age_preference=new_profile.min_age_preference,
        max_age_preference=new_profile.max_age_preference,
        max_distance_km=new_profile.max_distance_km,
        gender_preference=new_profile.gender_preference,
        is_complete=new_profile.is_complete,
        is_visible=new_profile.is_visible,
        photos=[],
        interests=[],
        created_at=new_profile.created_at,
        updated_at=new_profile.updated_at,
    )


@router.get("", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得自己的個人檔案"""
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos), selectinload(Profile.interests))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在，請先建立"
        )

    age = calculate_age(current_user.date_of_birth)
    return _build_profile_response(profile, age)


# ========== update_profile 輔助函數 ==========


async def _validate_bio_content(
    db: AsyncSession, user_id: uuid.UUID, bio: str | None
) -> tuple[bool, int, str | dict]:
    """驗證個人簡介內容

    Args:
        db: 資料庫 session
        user_id: 用戶 ID
        bio: 個人簡介內容

    Returns:
        (is_valid, status_code, error_detail)
    """
    if bio is None:
        return True, 0, ""

    is_approved, violations, action = await ContentModerationService.check_profile_content(
        db=db, user_id=user_id, bio=bio
    )
    if not is_approved:
        return False, status.HTTP_400_BAD_REQUEST, {
            "message": "個人簡介包含不當內容",
            "violations": violations,
            "action": action
        }
    return True, 0, ""


def _apply_profile_updates(profile: Profile, request: ProfileUpdateRequest) -> None:
    """套用所有欄位更新到 profile

    Args:
        profile: 個人檔案對象
        request: 更新請求
    """
    if request.display_name is not None:
        profile.display_name = request.display_name
    if request.gender is not None:
        profile.gender = request.gender.value
    if request.bio is not None:
        profile.bio = request.bio
    if request.location is not None:
        profile.location = ST_SetSRID(
            ST_MakePoint(request.location.longitude, request.location.latitude),
            4326
        )
        profile.location_name = request.location.location_name
    if request.min_age_preference is not None:
        profile.min_age_preference = request.min_age_preference
    if request.max_age_preference is not None:
        profile.max_age_preference = request.max_age_preference
    if request.max_distance_km is not None:
        profile.max_distance_km = request.max_distance_km
    if request.gender_preference is not None:
        profile.gender_preference = request.gender_preference.value


def _build_profile_response(
    profile: Profile,
    age: int,
    include_all_photos: bool = True
) -> ProfileResponse:
    """構建 ProfileResponse（共用輔助函數）

    Args:
        profile: 個人檔案對象（需預載入 photos 和 interests）
        age: 用戶年齡
        include_all_photos: 是否包含所有照片（含待審核）。用戶自己查看時為 True，其他人查看時為 False

    Returns:
        ProfileResponse 對象
    """
    # 過濾照片：用戶自己可看到所有照片，其他用戶只能看到已審核的照片
    filtered_photos = profile.photos if include_all_photos else [
        photo for photo in profile.photos
        if photo.moderation_status == "APPROVED"
    ]

    photos = [
        PhotoResponse(
            id=str(photo.id),
            url=photo.url,
            thumbnail_url=photo.thumbnail_url,
            display_order=photo.display_order,
            is_profile_picture=photo.is_profile_picture,
            moderation_status=photo.moderation_status,
            rejection_reason=photo.rejection_reason,
            created_at=photo.created_at
        )
        for photo in filtered_photos
    ]

    interests = [
        InterestTagResponse(
            id=str(tag.id),
            name=tag.name,
            category=tag.category,
            icon=tag.icon
        )
        for tag in profile.interests
    ]

    return ProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        gender=profile.gender,
        bio=profile.bio,
        location_name=profile.location_name,
        age=age,
        min_age_preference=profile.min_age_preference,
        max_age_preference=profile.max_age_preference,
        max_distance_km=profile.max_distance_km,
        gender_preference=profile.gender_preference,
        is_complete=profile.is_complete,
        is_visible=profile.is_visible,
        photos=photos,
        interests=interests,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新個人檔案"""
    # 1. 取得 profile
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos), selectinload(Profile.interests))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在，請先建立"
        )

    # 2. 內容審核
    is_valid, status_code, error = await _validate_bio_content(
        db, current_user.id, request.bio
    )
    if not is_valid:
        raise HTTPException(status_code=status_code, detail=error)

    # 3. 套用更新
    _apply_profile_updates(profile, request)

    # 4. 檢查完整度並儲存
    profile.is_complete = check_profile_completeness(profile)
    await db.commit()
    await db.refresh(profile)

    # 5. 回傳響應
    age = calculate_age(current_user.date_of_birth)
    return _build_profile_response(profile, age)


@router.put("/interests", response_model=ProfileResponse)
async def update_interests(
    request: UpdateInterestsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新興趣標籤（3-10個）"""
    # 取得檔案
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos), selectinload(Profile.interests))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在，請先建立"
        )

    # UUID 格式已在 Schema 層驗證，這裡直接轉換
    interest_uuids = [uuid.UUID(id_str) for id_str in request.interest_ids]

    # 驗證所有標籤都存在
    result = await db.execute(
        select(InterestTag).where(InterestTag.id.in_(interest_uuids))
    )
    tags = result.scalars().all()

    if len(tags) != len(request.interest_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部分興趣標籤不存在"
        )

    # 更新興趣標籤
    profile.interests = list(tags)

    # 檢查檔案完整度並儲存
    profile.is_complete = check_profile_completeness(profile)
    await db.commit()
    await db.refresh(profile)

    # 回傳響應
    age = calculate_age(current_user.date_of_birth)
    return _build_profile_response(profile, age)


# ========== upload_photo 輔助函數 ==========


def _validate_photo_content_type(content_type: str | None) -> tuple[bool, int, str]:
    """驗證照片 Content-Type

    Args:
        content_type: 檔案的 MIME 類型

    Returns:
        (is_valid, status_code, error_detail)
    """
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if content_type not in ALLOWED_TYPES:
        return (
            False,
            status.HTTP_400_BAD_REQUEST,
            "不支援的圖片格式，僅支援: jpg, jpeg, png, gif, webp",
        )
    return True, 0, ""


async def _read_file_with_size_limit(
    file: UploadFile,
    max_size: int = settings.MAX_UPLOAD_SIZE,
    chunk_size: int = 64 * 1024,
) -> tuple[bool, int, str, bytes | None]:
    """流式讀取檔案並限制大小（防止 DoS）

    Args:
        file: 上傳的檔案
        max_size: 最大允許大小（bytes）
        chunk_size: 讀取區塊大小

    Returns:
        (is_valid, status_code, error_detail, file_content)
    """
    chunks = []
    total_size = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            return (
                False,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"檔案過大，最大允許 {max_size / 1024 / 1024:.0f}MB",
                None,
            )
        chunks.append(chunk)

    file_content = b"".join(chunks)
    if len(file_content) == 0:
        return False, status.HTTP_400_BAD_REQUEST, "檔案不能為空", None

    return True, 0, "", file_content


def _validate_image_format(file_content: bytes) -> tuple[bool, int, str]:
    """驗證實際圖片格式（使用 PIL，防止偽造 Content-Type）

    Args:
        file_content: 檔案二進制內容

    Returns:
        (is_valid, status_code, error_detail)
    """
    ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
    try:
        img = Image.open(io.BytesIO(file_content))
        img.verify()
        if img.format not in ALLOWED_FORMATS:
            return False, status.HTTP_400_BAD_REQUEST, "無效的圖片格式"
    except (Image.UnidentifiedImageError, IOError, ValueError):
        return (
            False,
            status.HTTP_400_BAD_REQUEST,
            "無效的圖片檔案，請上傳有效的圖片",
        )
    return True, 0, ""


async def _get_profile_with_photos(
    user_id: uuid.UUID, db: AsyncSession
) -> tuple[bool, int, str, Profile | None]:
    """取得用戶個人檔案並檢查照片數量限制

    Args:
        user_id: 用戶 ID
        db: 資料庫 session

    Returns:
        (is_valid, status_code, error_detail, profile)
    """
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos), selectinload(Profile.interests))
        .where(Profile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return False, status.HTTP_404_NOT_FOUND, "個人檔案不存在，請先建立", None
    if len(profile.photos) >= 6:
        return False, status.HTTP_400_BAD_REQUEST, "最多只能上傳 6 張照片", None
    return True, 0, "", profile


async def _save_photo_file(
    user_id: uuid.UUID,
    file_content: bytes,
    filename: str | None,
    content_type: str | None,
) -> tuple[bool, int, str, tuple | None]:
    """儲存照片到本地儲存

    Args:
        user_id: 用戶 ID
        file_content: 檔案二進制內容
        filename: 原始檔名
        content_type: MIME 類型

    Returns:
        (success, status_code, error_detail, (photo_id, photo_url, thumbnail_url))
    """
    try:
        photo_id, photo_url, thumbnail_url = await file_storage.save_photo(
            user_id=str(user_id),
            file_content=file_content,
            filename=filename or "photo.jpg",
            content_type=content_type,
        )
        return True, 0, "", (photo_id, photo_url, thumbnail_url)
    except Exception as e:
        logger.error(f"Failed to save photo for user {user_id}: {e}")
        return (
            False,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "照片儲存失敗，請稍後再試",
            None,
        )


async def _create_photo_record(
    profile: Profile,
    photo_url: str,
    thumbnail_url: str,
    content_type: str | None,
    db: AsyncSession,
) -> tuple[bool, int, str, Photo | None]:
    """建立照片資料庫記錄並更新個人檔案完整度

    Args:
        profile: 個人檔案對象
        photo_url: 照片 URL
        thumbnail_url: 縮圖 URL
        content_type: MIME 類型
        db: 資料庫 session

    Returns:
        (success, status_code, error_detail, photo)
    """
    existing_count = len(profile.photos)
    new_photo = Photo(
        profile_id=profile.id,
        url=photo_url,
        thumbnail_url=thumbnail_url,
        display_order=existing_count,
        is_profile_picture=(existing_count == 0),
        mime_type=content_type,
        moderation_status="PENDING",  # 新上傳的照片預設待審核
    )

    try:
        db.add(new_photo)
        await db.flush()
        await db.refresh(profile, ["photos", "interests"])
        profile.is_complete = check_profile_completeness(profile)
        await db.commit()
        await db.refresh(new_photo)
        return True, 0, "", new_photo
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Failed to add photo for profile {profile.id}: {e}", exc_info=True
        )
        return (
            False,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "照片上傳失敗，請稍後再試",
            None,
        )


@router.post("/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上傳照片 - 協調器

    流程：
    1. 驗證 Content-Type
    2. 流式讀取並驗證大小
    3. 驗證圖片格式（PIL）
    4. 取得個人檔案並檢查照片數量
    5. 儲存照片檔案
    6. 建立資料庫記錄

    安全措施：
    - 檔案大小限制（5MB）
    - MIME 類型驗證
    - 實際圖片格式驗證（使用 PIL）
    """
    # 1. 驗證 Content-Type
    is_valid, status_code, error = _validate_photo_content_type(file.content_type)
    if not is_valid:
        raise HTTPException(status_code=status_code, detail=error)

    # 2. 流式讀取並驗證大小
    is_valid, status_code, error, file_content = await _read_file_with_size_limit(file)
    if not is_valid:
        raise HTTPException(status_code=status_code, detail=error)

    # 3. 驗證圖片格式（PIL）
    is_valid, status_code, error = _validate_image_format(file_content)
    if not is_valid:
        raise HTTPException(status_code=status_code, detail=error)

    # 4. 取得個人檔案並檢查照片數量
    is_valid, status_code, error, profile = await _get_profile_with_photos(
        current_user.id, db
    )
    if not is_valid:
        raise HTTPException(status_code=status_code, detail=error)

    # 5. 儲存照片檔案
    success, status_code, error, photo_data = await _save_photo_file(
        current_user.id, file_content, file.filename, file.content_type
    )
    if not success:
        raise HTTPException(status_code=status_code, detail=error)

    _, photo_url, thumbnail_url = photo_data

    # 6. 建立資料庫記錄
    success, status_code, error, new_photo = await _create_photo_record(
        profile, photo_url, thumbnail_url, file.content_type, db
    )
    if not success:
        raise HTTPException(status_code=status_code, detail=error)

    return PhotoResponse(
        id=str(new_photo.id),
        url=new_photo.url,
        thumbnail_url=new_photo.thumbnail_url,
        display_order=new_photo.display_order,
        is_profile_picture=new_photo.is_profile_picture,
        moderation_status=new_photo.moderation_status,
        rejection_reason=new_photo.rejection_reason,
        created_at=new_photo.created_at,
    )


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """刪除照片"""
    # 取得照片
    result = await db.execute(
        select(Photo)
        .join(Profile)
        .where(
            Photo.id == photo_id,
            Profile.user_id == current_user.id
        )
    )
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="照片不存在"
        )

    # 取得 profile 以便檢查完整度和重新排序
    profile_id = photo.profile_id
    deleted_order = photo.display_order
    photo_url = photo.url
    thumbnail_url = photo.thumbnail_url

    # 先刪除實際檔案（避免資料庫提交後檔案刪除失敗導致不一致）
    try:
        await file_storage.delete_photo(photo_url)
        if thumbnail_url:
            await file_storage.delete_photo(thumbnail_url)
    except Exception as e:
        logger.error(f"Failed to delete photo files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="照片檔案刪除失敗"
        )

    # 檔案刪除成功後，再刪除資料庫記錄
    await db.delete(photo)
    await db.commit()

    # 重新載入 profile 及其照片
    result = await db.execute(
        select(Profile)
        .options(
            selectinload(Profile.photos),
            selectinload(Profile.interests)
        )
        .where(Profile.id == profile_id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        # 重新排序照片（讓順序連續）
        remaining_photos = sorted(profile.photos, key=lambda p: p.display_order)
        for index, photo_item in enumerate(remaining_photos):
            photo_item.display_order = index

        # 如果刪除的是第一張照片，且還有其他照片，將第一張照片設為主頭像
        if deleted_order == 0 and remaining_photos:
            # 先清除所有照片的主頭像標記
            for photo_item in remaining_photos:
                photo_item.is_profile_picture = False
            # 將第一張設為主頭像
            remaining_photos[0].is_profile_picture = True

        # 檢查檔案完整度
        profile.is_complete = check_profile_completeness(profile)
        await db.commit()


@router.put("/photos/order", response_model=List[PhotoResponse])
async def reorder_photos(
    request: PhotoOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """調整照片順序

    根據傳入的照片 ID 陣列重新排序所有照片。
    陣列中的順序即為新的 display_order。

    驗證規則：
    - photo_ids 數量必須與用戶現有照片數量一致
    - 所有 photo_ids 必須屬於該用戶
    """
    # 取得用戶的 Profile 及其照片
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在"
        )

    existing_photos = {str(photo.id): photo for photo in profile.photos}
    existing_count = len(existing_photos)

    # 驗證 photo_ids 數量
    if len(request.photo_ids) != existing_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"照片數量不符：預期 {existing_count} 張，收到 {len(request.photo_ids)} 張"
        )

    # 驗證所有 photo_ids 都屬於該用戶，且無重複
    seen_ids = set()
    for photo_id in request.photo_ids:
        if photo_id in seen_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"重複的照片 ID：{photo_id}"
            )
        seen_ids.add(photo_id)

        if photo_id not in existing_photos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"照片 ID 不存在或不屬於此用戶：{photo_id}"
            )

    # 更新 display_order
    for new_order, photo_id in enumerate(request.photo_ids):
        existing_photos[photo_id].display_order = new_order

    await db.commit()

    # 返回排序後的照片列表
    sorted_photos = sorted(profile.photos, key=lambda p: p.display_order)
    return [
        PhotoResponse(
            id=str(photo.id),
            url=photo.url,
            thumbnail_url=photo.thumbnail_url,
            display_order=photo.display_order,
            is_profile_picture=photo.is_profile_picture,
            moderation_status=photo.moderation_status,
            rejection_reason=photo.rejection_reason,
            created_at=photo.created_at,
        )
        for photo in sorted_photos
    ]


@router.put("/photos/{photo_id}/primary", response_model=PhotoResponse)
async def set_profile_picture(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """設定主頭像

    將指定照片設為主頭像，並自動移到第一位。
    只有已通過審核 (APPROVED) 的照片可以設為主頭像。
    """
    # 取得用戶的 Profile 及其照片
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.photos))
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在"
        )

    # 找到目標照片
    target_photo = None
    for photo in profile.photos:
        if str(photo.id) == photo_id:
            target_photo = photo
            break

    if not target_photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="照片不存在或不屬於此用戶"
        )

    # 檢查審核狀態
    if target_photo.moderation_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有已通過審核的照片可以設為主頭像"
        )

    # 更新主頭像標記並重新排序
    old_order = target_photo.display_order

    for photo in profile.photos:
        if str(photo.id) == photo_id:
            photo.is_profile_picture = True
            photo.display_order = 0  # 移到第一位
        else:
            photo.is_profile_picture = False
            # 原本在目標照片前面的照片，順序 +1
            if photo.display_order < old_order:
                photo.display_order += 1

    await db.commit()
    await db.refresh(target_photo)

    return PhotoResponse(
        id=str(target_photo.id),
        url=target_photo.url,
        thumbnail_url=target_photo.thumbnail_url,
        display_order=target_photo.display_order,
        is_profile_picture=target_photo.is_profile_picture,
        moderation_status=target_photo.moderation_status,
        rejection_reason=target_photo.rejection_reason,
        created_at=target_photo.created_at,
    )


@router.get("/interest-tags", response_model=List[InterestTagResponse])
async def get_interest_tags(
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """取得所有興趣標籤"""
    query = select(InterestTag).where(InterestTag.is_active.is_(True))

    if category:
        query = query.where(InterestTag.category == category)

    result = await db.execute(query.order_by(InterestTag.category, InterestTag.name))
    tags = result.scalars().all()

    return [
        InterestTagResponse(
            id=str(tag.id),
            name=tag.name,
            category=tag.category,
            icon=tag.icon
        )
        for tag in tags
    ]


@router.post(
    "/interest-tags",
    response_model=InterestTagResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_interest_tag(
    request: InterestTagCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """建立興趣標籤（僅管理員）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )

    # 檢查標籤是否已存在
    result = await db.execute(
        select(InterestTag).where(InterestTag.name == request.name)
    )
    existing_tag = result.scalar_one_or_none()

    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="標籤已存在"
        )

    # 建立標籤
    new_tag = InterestTag(
        name=request.name,
        category=request.category,
        icon=request.icon,
    )

    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)

    return InterestTagResponse(
        id=str(new_tag.id),
        name=new_tag.name,
        category=new_tag.category,
        icon=new_tag.icon
    )
