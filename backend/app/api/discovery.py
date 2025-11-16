"""探索與配對 API"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, not_, func, case
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from geoalchemy2.functions import ST_Distance, ST_DWithin
from typing import Optional, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.profile import Profile
from app.models.match import Like, Match, BlockedUser, Message
from app.schemas.discovery import ProfileCard, LikeResponse, MatchSummary, MatchDetail
from app.services.matching_service import matching_service

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


@router.get("/browse", response_model=List[ProfileCard])
async def browse_users(
    limit: int = Query(20, ge=1, le=50, description="返回數量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    瀏覽可配對用戶

    篩選條件:
    - 根據用戶的偏好設定（年齡、距離、性別）
    - 排除已喜歡、已配對、已封鎖的用戶
    - 按配對分數排序
    """
    # 取得當前用戶的 profile（預先加載 interests）
    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.interests))
        .where(Profile.user_id == current_user.id)
    )
    my_profile = result.scalar_one_or_none()

    if not my_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="請先完成個人檔案設定"
        )

    if not my_profile.location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="請先設定您的位置"
        )

    # 使用用戶的偏好設定
    min_age = my_profile.min_age_preference or 18
    max_age = my_profile.max_age_preference or 99
    max_distance_km = my_profile.max_distance_km or 50
    gender_preference = my_profile.gender_preference

    # 計算年齡範圍的出生日期
    today = datetime.today().date()
    max_birth_date = today - relativedelta(years=min_age)
    min_birth_date = today - relativedelta(years=max_age + 1)

    # 建立主查詢（預先加載 relationships 和計算距離）
    # 計算距離作為標籤，避免 N+1 查詢
    distance_label = (
        func.ST_Distance(
            Profile.location,
            my_profile.location,
            True  # use_spheroid=True
        ) / 1000  # 轉換為公里
    ).label('distance_km')

    query = (
        select(Profile, distance_label)
        .join(User, Profile.user_id == User.id)
        .options(
            selectinload(Profile.user),
            selectinload(Profile.photos),
            selectinload(Profile.interests)
        )
        .where(
            and_(
                Profile.user_id != current_user.id,
                Profile.is_visible == True,
                Profile.is_complete == True,
                User.is_active == True,
                # 年齡篩選
                User.date_of_birth >= min_birth_date,
                User.date_of_birth <= max_birth_date,
                # 距離篩選 (PostGIS)
                ST_DWithin(
                    Profile.location,
                    my_profile.location,
                    max_distance_km * 1000,  # 轉換為公尺
                    True  # use_spheroid=True，使用球面計算
                )
            )
        )
    )

    # 性別篩選
    if gender_preference and gender_preference != "all":
        if gender_preference == "both":
            query = query.where(Profile.gender.in_(["male", "female"]))
        else:
            query = query.where(Profile.gender == gender_preference)

    # 排除已喜歡的用戶（包括互相喜歡的）
    liked_users_subquery = select(Like.to_user_id).where(
        Like.from_user_id == current_user.id
    )
    query = query.where(Profile.user_id.notin_(liked_users_subquery))

    # 排除已配對的用戶
    matched_users_subquery = select(
        case(
            (Match.user1_id == current_user.id, Match.user2_id),
            else_=Match.user1_id
        )
    ).where(
        or_(
            Match.user1_id == current_user.id,
            Match.user2_id == current_user.id
        ),
        Match.status == "ACTIVE"
    )
    query = query.where(Profile.user_id.notin_(matched_users_subquery))

    # 排除已封鎖的用戶
    blocked_subquery = select(BlockedUser.blocked_id).where(
        BlockedUser.blocker_id == current_user.id
    )
    query = query.where(Profile.user_id.notin_(blocked_subquery))

    # 排除封鎖我的用戶
    blocked_me_subquery = select(BlockedUser.blocker_id).where(
        BlockedUser.blocked_id == current_user.id
    )
    query = query.where(Profile.user_id.notin_(blocked_me_subquery))

    # 限制數量（先取較多候選人，稍後排序後再限制）
    query = query.limit(limit * 3)

    # 執行查詢（優化：距離已在查詢中計算，避免 N+1 問題）
    result = await db.execute(query)
    rows = result.all()

    # 轉換為 ProfileCard 格式並計算配對分數
    profile_cards = []
    for row in rows:
        profile = row[0]  # Profile 對象
        distance_km = row[1]  # 距離（已在查詢中計算）

        # 計算年齡
        age = relativedelta(today, profile.user.date_of_birth).years

        # 取得興趣標籤
        interests = [interest.name for interest in profile.interests]

        # 取得照片
        photos = [photo.url for photo in sorted(profile.photos, key=lambda p: p.display_order)]

        # 建立候選人資料字典（用於計算分數）
        candidate_data = {
            "interests": interests,
            "distance_km": distance_km,
            "last_active": profile.last_active,
            "photo_count": len(photos),
            "bio": profile.bio,
            "age": age
        }

        # 建立用戶偏好資料字典
        user_data = {
            "interests": [interest.name for interest in my_profile.interests],
            "min_age_preference": min_age,
            "max_age_preference": max_age,
            "max_distance_km": max_distance_km,
            "gender_preference": gender_preference
        }

        # 計算配對分數
        match_score = matching_service.calculate_match_score(user_data, candidate_data)

        # 建立 ProfileCard
        profile_card = ProfileCard(
            user_id=profile.user_id,
            display_name=profile.display_name,
            age=age,
            gender=profile.gender,
            bio=profile.bio,
            location_name=profile.location_name,
            distance_km=round(distance_km, 1) if distance_km else None,
            interests=interests,
            photos=photos,
            match_score=round(match_score, 1)
        )

        profile_cards.append(profile_card)

    # 依配對分數排序（高到低）
    profile_cards.sort(key=lambda x: x.match_score or 0, reverse=True)

    # 限制返回數量
    return profile_cards[:limit]


@router.post("/like/{user_id}", response_model=LikeResponse)
async def like_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    喜歡用戶

    - 建立喜歡記錄
    - 檢查是否互相喜歡
    - 如果互相喜歡，建立配對
    """
    # 不能喜歡自己
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能喜歡自己"
        )

    # 檢查是否已經喜歡
    result = await db.execute(
        select(Like).where(
            and_(
                Like.from_user_id == current_user.id,
                Like.to_user_id == user_id
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已經喜歡過此用戶"
        )

    # 檢查對方用戶是否存在且可見
    result = await db.execute(
        select(Profile).where(
            and_(
                Profile.user_id == user_id,
                Profile.is_visible == True,
                Profile.is_complete == True
            )
        )
    )
    target_profile = result.scalar_one_or_none()
    if not target_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在或不可見"
        )

    # 建立喜歡記錄（修復：使用資料庫唯一約束處理並發點讚）
    like = Like(
        from_user_id=current_user.id,
        to_user_id=user_id
    )
    db.add(like)

    try:
        await db.flush()  # 先刷新以檢測唯一約束
    except IntegrityError:
        # 並發情況下，另一個請求已創建了同樣的喜歡記錄
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已經喜歡過此用戶"
        )

    # 檢查對方是否也喜歡我
    result = await db.execute(
        select(Like).where(
            and_(
                Like.from_user_id == user_id,
                Like.to_user_id == current_user.id
            )
        )
    )
    mutual_like = result.scalar_one_or_none()

    is_match = False
    match_id = None

    if mutual_like:
        # 建立配對（保證 user1_id < user2_id）
        user1_id = min(current_user.id, user_id, key=lambda x: str(x))
        user2_id = max(current_user.id, user_id, key=lambda x: str(x))

        # 檢查是否已存在配對
        result = await db.execute(
            select(Match).where(
                and_(
                    Match.user1_id == user1_id,
                    Match.user2_id == user2_id
                )
            )
        )
        existing_match = result.scalar_one_or_none()

        if existing_match:
            # 如果配對曾經取消，重新啟用
            if existing_match.status == "UNMATCHED":
                existing_match.status = "ACTIVE"
                existing_match.matched_at = func.now()
                existing_match.unmatched_at = None
                existing_match.unmatched_by = None
                match_id = existing_match.id
        else:
            # 建立新配對
            match = Match(
                user1_id=user1_id,
                user2_id=user2_id,
                status="ACTIVE"
            )
            db.add(match)
            try:
                await db.flush()
                match_id = match.id
            except IntegrityError:
                # 並發情況下，另一個請求已創建了配對
                # 重要：不要 rollback！否則會回滾前面的 like 記錄
                # 直接重新查詢已存在的配對即可
                db.expunge(match)  # 從 session 移除失敗的 match 對象
                result = await db.execute(
                    select(Match).where(
                        and_(
                            Match.user1_id == user1_id,
                            Match.user2_id == user2_id
                        )
                    )
                )
                existing_match = result.scalar_one_or_none()
                if existing_match:
                    match_id = existing_match.id
                else:
                    # 如果還是查不到，說明有其他問題
                    await db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="配對創建失敗"
                    )

        is_match = True

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise

    return LikeResponse(
        liked=True,
        is_match=is_match,
        match_id=match_id
    )


@router.post("/pass/{user_id}")
async def pass_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    跳過用戶

    註：目前簡化實作，跳過不留記錄
    未來可以加入「跳過記錄」以避免重複顯示
    """
    # 不能跳過自己
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能跳過自己"
        )

    return {"passed": True, "message": "已跳過此用戶"}


@router.get("/matches", response_model=List[MatchSummary])
async def get_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得我的所有配對

    返回配對列表，包含對方的基本資訊

    優化：批次載入資料，避免 N+1 查詢問題
    """
    # 查詢所有活躍的配對
    result = await db.execute(
        select(Match).where(
            and_(
                or_(
                    Match.user1_id == current_user.id,
                    Match.user2_id == current_user.id
                ),
                Match.status == "ACTIVE"
            )
        ).order_by(Match.matched_at.desc())
    )
    matches = result.scalars().all()

    if not matches:
        return []

    # 批次載入：收集所有需要的 ID
    match_ids = [match.id for match in matches]
    matched_user_ids = [
        match.user2_id if match.user1_id == current_user.id else match.user1_id
        for match in matches
    ]

    # 批次查詢 1：所有配對用戶的 profiles（1 次查詢取代 N 次）
    profiles_result = await db.execute(
        select(Profile)
        .options(
            selectinload(Profile.user),
            selectinload(Profile.photos),
            selectinload(Profile.interests)
        )
        .where(Profile.user_id.in_(matched_user_ids))
    )
    profiles_by_user_id = {p.user_id: p for p in profiles_result.scalars().all()}

    # 批次查詢 2：所有未讀訊息數（1 次查詢取代 N 次）
    unread_counts_result = await db.execute(
        select(
            Message.match_id,
            func.count(Message.id).label('count')
        )
        .where(
            and_(
                Message.match_id.in_(match_ids),
                Message.sender_id.in_(matched_user_ids),
                Message.is_read.is_(None),
                Message.deleted_at.is_(None)
            )
        )
        .group_by(Message.match_id)
    )
    unread_counts_by_match = {row.match_id: row.count for row in unread_counts_result.all()}

    # 組裝回應
    today = datetime.today().date()
    match_summaries = []

    for match in matches:
        # 取得配對對象的 user_id
        matched_user_id = match.user2_id if match.user1_id == current_user.id else match.user1_id

        # 從批次載入的數據中獲取
        matched_profile = profiles_by_user_id.get(matched_user_id)

        if not matched_profile:
            continue

        # 計算年齡
        age = relativedelta(today, matched_profile.user.date_of_birth).years

        # 取得興趣和照片
        interests = [interest.name for interest in matched_profile.interests]
        photos = [photo.url for photo in sorted(matched_profile.photos, key=lambda p: p.display_order)]

        # 建立 ProfileCard
        profile_card = ProfileCard(
            user_id=matched_profile.user_id,
            display_name=matched_profile.display_name,
            age=age,
            gender=matched_profile.gender,
            bio=matched_profile.bio,
            location_name=matched_profile.location_name,
            interests=interests,
            photos=photos
        )

        # 從批次載入的數據中獲取未讀數
        unread_count = unread_counts_by_match.get(match.id, 0)

        match_summary = MatchSummary(
            match_id=match.id,
            matched_user=profile_card,
            matched_at=match.matched_at,
            unread_count=unread_count
        )

        match_summaries.append(match_summary)

    return match_summaries


@router.delete("/unmatch/{match_id}")
async def unmatch(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取消配對

    - 將配對狀態設為 UNMATCHED
    - 記錄取消者和取消時間
    """
    # 查詢配對
    result = await db.execute(
        select(Match).where(
            and_(
                Match.id == match_id,
                or_(
                    Match.user1_id == current_user.id,
                    Match.user2_id == current_user.id
                ),
                Match.status == "ACTIVE"
            )
        )
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配對不存在或已取消"
        )

    # 更新配對狀態
    match.status = "UNMATCHED"
    match.unmatched_at = func.now()
    match.unmatched_by = current_user.id

    await db.commit()

    return {"message": "已取消配對"}
