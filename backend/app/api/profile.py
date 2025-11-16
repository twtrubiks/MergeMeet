"""個人檔案相關 API"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
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
)
from app.services.content_moderation import ContentModerationService

router = APIRouter(prefix="/api/profile")


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

    # 設置地理位置
    if request.location:
        new_profile.location = f"SRID=4326;POINT({request.location.longitude} {request.location.latitude})"
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
        .options(
            selectinload(Profile.photos),
            selectinload(Profile.interests)
        )
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在，請先建立"
        )

    # 計算年齡
    age = calculate_age(current_user.date_of_birth)

    # 轉換照片
    photos = [
        PhotoResponse(
            id=str(photo.id),
            url=photo.url,
            thumbnail_url=photo.thumbnail_url,
            display_order=photo.display_order,
            is_profile_picture=photo.is_profile_picture,
            created_at=photo.created_at
        )
        for photo in profile.photos
    ]

    # 轉換興趣標籤
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
    result = await db.execute(
        select(Profile)
        .options(
            selectinload(Profile.photos),
            selectinload(Profile.interests)
        )
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在，請先建立"
        )

    # 內容審核：檢查個人簡介
    if request.bio is not None:
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

    # 更新欄位
    if request.display_name is not None:
        profile.display_name = request.display_name
    if request.gender is not None:
        profile.gender = request.gender.value
    if request.bio is not None:
        profile.bio = request.bio
    if request.location is not None:
        profile.location = f"SRID=4326;POINT({request.location.longitude} {request.location.latitude})"
        profile.location_name = request.location.location_name
    if request.min_age_preference is not None:
        profile.min_age_preference = request.min_age_preference
    if request.max_age_preference is not None:
        profile.max_age_preference = request.max_age_preference
    if request.max_distance_km is not None:
        profile.max_distance_km = request.max_distance_km
    if request.gender_preference is not None:
        profile.gender_preference = request.gender_preference.value

    # 檢查檔案完整度
    profile.is_complete = check_profile_completeness(profile)

    await db.commit()
    await db.refresh(profile)

    # 計算年齡
    age = calculate_age(current_user.date_of_birth)

    # 轉換照片和興趣
    photos = [
        PhotoResponse(
            id=str(photo.id),
            url=photo.url,
            thumbnail_url=photo.thumbnail_url,
            display_order=photo.display_order,
            is_profile_picture=photo.is_profile_picture,
            created_at=photo.created_at
        )
        for photo in profile.photos
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
        .options(
            selectinload(Profile.photos),
            selectinload(Profile.interests)
        )
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在，請先建立"
        )

    # 轉換字串 ID 為 UUID 對象
    try:
        interest_uuids = [uuid.UUID(id_str) for id_str in request.interest_ids]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的標籤 ID 格式"
        )

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

    # 檢查檔案完整度
    profile.is_complete = check_profile_completeness(profile)

    await db.commit()
    await db.refresh(profile)

    # 計算年齡
    age = calculate_age(current_user.date_of_birth)

    # 轉換照片和興趣
    photos = [
        PhotoResponse(
            id=str(photo.id),
            url=photo.url,
            thumbnail_url=photo.thumbnail_url,
            display_order=photo.display_order,
            is_profile_picture=photo.is_profile_picture,
            created_at=photo.created_at
        )
        for photo in profile.photos
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


@router.post("/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上傳照片（簡化版）

    注意：此版本暫不實際處理圖片，僅模擬上傳流程
    """
    # 取得檔案（一次性載入照片和興趣以便後續檢查完整度）
    result = await db.execute(
        select(Profile)
        .options(
            selectinload(Profile.photos),
            selectinload(Profile.interests)
        )
        .where(Profile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在，請先建立"
        )

    # 檢查照片數量（最多 6 張）
    existing_photos = profile.photos

    if len(existing_photos) >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="最多只能上傳 6 張照片"
        )

    # 驗證檔案類型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能上傳圖片檔案"
        )

    # 生成模擬 URL（實際應用應上傳到儲存服務）
    photo_id = uuid.uuid4()
    mock_url = f"/uploads/photos/{current_user.id}/{photo_id}.jpg"
    mock_thumbnail = f"/uploads/photos/{current_user.id}/{photo_id}_thumb.jpg"

    # 建立照片記錄
    new_photo = Photo(
        profile_id=profile.id,
        url=mock_url,
        thumbnail_url=mock_thumbnail,
        display_order=len(existing_photos),
        is_profile_picture=(len(existing_photos) == 0),  # 第一張設為頭像
        mime_type=file.content_type,
    )

    db.add(new_photo)
    await db.commit()
    await db.refresh(new_photo)

    # 重新載入 profile 的關聯以檢查完整度
    await db.refresh(profile, ["photos", "interests"])
    profile.is_complete = check_profile_completeness(profile)
    await db.commit()

    return PhotoResponse(
        id=str(new_photo.id),
        url=new_photo.url,
        thumbnail_url=new_photo.thumbnail_url,
        display_order=new_photo.display_order,
        is_profile_picture=new_photo.is_profile_picture,
        created_at=new_photo.created_at
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


@router.get("/interest-tags", response_model=List[InterestTagResponse])
async def get_interest_tags(
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """取得所有興趣標籤"""
    query = select(InterestTag).where(InterestTag.is_active == True)

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


@router.post("/interest-tags", response_model=InterestTagResponse, status_code=status.HTTP_201_CREATED)
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
