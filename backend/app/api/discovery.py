"""探索與配對 API

TODO [Redis 擴展] 效能優化時可加入 Redis 快取

目前每次請求都直接查詢資料庫。當用戶量增加、查詢效能成為瓶頸時，
可以考慮使用 Redis 快取以下資料：

1. 推薦用戶快取（browse_users）：
   Redis Key 設計：
   - discovery:browse:{user_id}:{hash(偏好設定)} - 推薦用戶 ID 列表 (List, TTL: 5-10 分鐘)
   - 當用戶更新偏好設定時，清除該用戶的快取

2. 配對列表快取（get_matches）：
   Redis Key 設計：
   - discovery:matches:{user_id} - 配對摘要 JSON (String, TTL: 1-2 分鐘)
   - 當有新配對、配對狀態變更、新訊息時，清除相關用戶的快取

3. 熱門用戶快取：
   Redis Key 設計：
   - discovery:popular - 熱門用戶 ID 列表 (Sorted Set by 活躍度分數)
   - 定期更新（每小時）

快取失效策略：
- 用戶互動（like/pass/unmatch）時主動清除相關快取
- 使用較短的 TTL 確保資料新鮮度
- 可考慮使用 Redis 的 pub/sub 做跨實例快取失效通知
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, case, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from geoalchemy2.functions import ST_DWithin
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import uuid
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.profile import Profile
from app.models.match import Like, Match, BlockedUser, Message, Pass
from app.models.notification import Notification
from app.schemas.discovery import ProfileCard, LikeResponse, MatchSummary
from app.services.matching_service import matching_service
from app.services.trust_score import TrustScoreService

logger = logging.getLogger(__name__)

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
                Profile.is_visible.is_(True),
                Profile.is_complete.is_(True),
                User.is_active.is_(True),
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

    # 排除 24 小時內跳過的用戶（類似 Tinder 做法）
    pass_cutoff = datetime.now() - timedelta(hours=24)
    passed_users_subquery = select(Pass.to_user_id).where(
        Pass.from_user_id == current_user.id,
        Pass.passed_at > pass_cutoff  # 只排除 24 小時內跳過的
    )
    query = query.where(Profile.user_id.notin_(passed_users_subquery))

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
            "age": age,
            "trust_score": profile.user.trust_score  # 信任分數
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


# ========== like_user 輔助函數 ==========


def _get_user_avatar(profile: Profile) -> Optional[str]:
    """取得用戶頭像 URL

    Args:
        profile: 用戶的 Profile 對象

    Returns:
        頭像 URL，如果沒有則返回 None
    """
    if not profile or not profile.photos:
        return None
    # 優先取 is_profile_picture 的照片
    profile_photo = next((p for p in profile.photos if p.is_profile_picture), None)
    if profile_photo:
        return profile_photo.url
    # 否則取第一張照片
    return profile.photos[0].url if profile.photos else None


async def _validate_like_request(
    user_id: uuid.UUID,
    current_user: User,
    db: AsyncSession
) -> tuple[bool, int, str, Optional[Profile]]:
    """驗證喜歡請求

    驗證:
    - 不能喜歡自己
    - 是否已經喜歡過
    - 對方用戶是否存在且可見

    Args:
        user_id: 目標用戶 ID
        current_user: 當前用戶
        db: 資料庫 session

    Returns:
        (is_valid, status_code, error_detail, target_profile)
    """
    # 不能喜歡自己
    if user_id == current_user.id:
        return False, status.HTTP_400_BAD_REQUEST, "不能喜歡自己", None

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
        return False, status.HTTP_400_BAD_REQUEST, "已經喜歡過此用戶", None

    # 檢查對方用戶是否存在且可見
    result = await db.execute(
        select(Profile).where(
            and_(
                Profile.user_id == user_id,
                Profile.is_visible.is_(True),
                Profile.is_complete.is_(True)
            )
        )
    )
    target_profile = result.scalar_one_or_none()
    if not target_profile:
        return False, status.HTTP_404_NOT_FOUND, "用戶不存在或不可見", None

    return True, 0, "", target_profile


async def _create_like_record(
    from_user_id: uuid.UUID,
    to_user_id: uuid.UUID,
    db: AsyncSession
) -> tuple[bool, int, str, Optional[Like]]:
    """創建 Like 記錄（含並發處理）

    Args:
        from_user_id: 發起者 ID
        to_user_id: 目標用戶 ID
        db: 資料庫 session

    Returns:
        (success, status_code, error_detail, like_record)
    """
    like = Like(
        from_user_id=from_user_id,
        to_user_id=to_user_id
    )
    db.add(like)

    try:
        await db.flush()  # 先刷新以檢測唯一約束
        return True, 0, "", like
    except IntegrityError:
        # 並發情況下，另一個請求已創建了同樣的喜歡記錄
        await db.rollback()
        return False, status.HTTP_400_BAD_REQUEST, "已經喜歡過此用戶", None


async def _check_mutual_like_and_create_match(
    current_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    db: AsyncSession
) -> tuple[bool, Optional[uuid.UUID], Optional[str]]:
    """檢查是否互相喜歡並創建配對

    Args:
        current_user_id: 當前用戶 ID
        target_user_id: 目標用戶 ID
        db: 資料庫 session

    Returns:
        (is_match, match_id, error_detail)
    """
    # 檢查對方是否也喜歡我（使用 SELECT FOR UPDATE 鎖定，避免競態條件）
    result = await db.execute(
        select(Like).where(
            and_(
                Like.from_user_id == target_user_id,
                Like.to_user_id == current_user_id
            )
        ).with_for_update()
    )
    mutual_like = result.scalar_one_or_none()

    if not mutual_like:
        return False, None, None

    # 有互相喜歡，建立配對
    # 保證 user1_id < user2_id
    user1_id = min(current_user_id, target_user_id, key=lambda x: str(x))
    user2_id = max(current_user_id, target_user_id, key=lambda x: str(x))

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
        return True, existing_match.id, None

    # 建立新配對
    match = Match(
        user1_id=user1_id,
        user2_id=user2_id,
        status="ACTIVE"
    )
    db.add(match)

    try:
        await db.flush()
        return True, match.id, None
    except IntegrityError:
        # 並發情況下，另一個請求已創建了配對
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
            return True, existing_match.id, None
        # 如果還是查不到，說明有其他問題
        await db.rollback()
        return False, None, "配對創建失敗"


async def _send_like_notifications(
    is_match: bool,
    match_id: Optional[uuid.UUID],
    current_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    db: AsyncSession
) -> None:
    """發送喜歡/配對通知（含持久化）

    Args:
        is_match: 是否為配對
        match_id: 配對 ID（如果是配對）
        current_user_id: 當前用戶 ID
        target_user_id: 目標用戶 ID
        db: 資料庫 session
    """
    # 在函數內部 import 避免循環依賴
    from app.websocket.manager import manager

    if is_match and match_id:
        # 【通知類型 1】新配對通知 (notification_match)
        # 查詢當前用戶的 Profile 資訊（用於通知內容）
        current_profile_result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.photos))
            .where(Profile.user_id == current_user_id)
        )
        current_profile = current_profile_result.scalar_one_or_none()

        # 查詢對方的 Profile 資訊（用 selectinload 載入 photos）
        target_profile_result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.photos))
            .where(Profile.user_id == target_user_id)
        )
        target_profile = target_profile_result.scalar_one_or_none()

        current_name = current_profile.display_name if current_profile else "用戶"
        target_name = target_profile.display_name if target_profile else "用戶"
        current_avatar = _get_user_avatar(current_profile)
        target_avatar = _get_user_avatar(target_profile)

        # 持久化通知到資料庫（給對方）
        notification_for_target = Notification(
            user_id=target_user_id,
            type="notification_match",
            title="新配對成功！",
            content=f"你和 {current_name} 配對成功了！",
            data={
                "match_id": str(match_id),
                "matched_user_id": str(current_user_id),
                "matched_user_name": current_name,
                "matched_user_avatar": current_avatar
            }
        )
        db.add(notification_for_target)

        # 持久化通知到資料庫（給當前用戶）
        notification_for_current = Notification(
            user_id=current_user_id,
            type="notification_match",
            title="新配對成功！",
            content=f"你和 {target_name} 配對成功了！",
            data={
                "match_id": str(match_id),
                "matched_user_id": str(target_user_id),
                "matched_user_name": target_name,
                "matched_user_avatar": target_avatar
            }
        )
        db.add(notification_for_current)
        await db.commit()
        logger.info(f"Persisted notification_match for users {target_user_id} and {current_user_id}")

        # 發送 WebSocket 通知給對方（配對成功）
        await manager.send_personal_message(
            str(target_user_id),
            {
                "type": "notification_match",
                "match_id": str(match_id),
                "matched_user_id": str(current_user_id),
                "matched_user_name": current_name,
                "matched_user_avatar": current_avatar,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        logger.info(f"Sent notification_match to user {target_user_id} for match {match_id}")

        # 發送 WebSocket 通知給當前用戶（配對成功）
        await manager.send_personal_message(
            str(current_user_id),
            {
                "type": "notification_match",
                "match_id": str(match_id),
                "matched_user_id": str(target_user_id),
                "matched_user_name": target_name,
                "matched_user_avatar": target_avatar,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        logger.info(f"Sent notification_match to user {current_user_id} for match {match_id}")
    else:
        # 【通知類型 2】有人喜歡你通知 (notification_liked)
        # 對方還沒喜歡我，發送「有人喜歡你」通知給對方
        # 注意：不透露是誰喜歡，保持神秘感

        # 持久化通知到資料庫
        notification_liked = Notification(
            user_id=target_user_id,
            type="notification_liked",
            title="有人喜歡你！",
            content="有人對你心動了，快去探索看看吧！",
            data={}
        )
        db.add(notification_liked)
        await db.commit()
        logger.info(f"Persisted notification_liked for user {target_user_id}")

        # 發送 WebSocket 通知
        await manager.send_personal_message(
            str(target_user_id),
            {
                "type": "notification_liked",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        logger.info(f"Sent notification_liked to user {target_user_id}")


@router.post("/like/{user_id}", response_model=LikeResponse)
async def like_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """喜歡用戶 - 協調器

    流程：
    1. 驗證請求（不能喜歡自己、已喜歡、對方存在）
    2. 創建 Like 記錄
    3. 檢查互相喜歡並創建配對
    4. 提交事務
    5. 發送通知
    """
    # 1. 驗證請求
    is_valid, status_code, error, _ = await _validate_like_request(
        user_id, current_user, db
    )
    if not is_valid:
        raise HTTPException(status_code=status_code, detail=error)

    # 2. 創建 Like 記錄
    success, status_code, error, _ = await _create_like_record(
        current_user.id, user_id, db
    )
    if not success:
        raise HTTPException(status_code=status_code, detail=error)

    # 3. 檢查互相喜歡並創建配對
    is_match, match_id, error = await _check_mutual_like_and_create_match(
        current_user.id, user_id, db
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    # 4. 提交事務
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    # 5. 信任分數調整
    # 被喜歡者 +1 分
    await TrustScoreService.adjust_score(db, user_id, "received_like")
    logger.info(f"Trust score +1 for user {user_id} (received_like)")

    # 配對成功時：雙方各 +2 分
    if is_match:
        await TrustScoreService.adjust_score(db, current_user.id, "match_created")
        await TrustScoreService.adjust_score(db, user_id, "match_created")
        logger.info(f"Trust score +2 for users {current_user.id} and {user_id} (match_created)")

    # 6. 發送通知
    await _send_like_notifications(
        is_match, match_id, current_user.id, user_id, db
    )

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

    記錄跳過操作，24 小時內跳過的用戶不會再次出現。
    24 小時後可重新配對（類似 Tinder），給用戶第二次機會。
    """
    # 不能跳過自己
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能跳過自己"
        )

    # 創建或更新跳過記錄（先查詢再決定）
    # 檢查是否已經跳過過
    result = await db.execute(
        select(Pass).where(
            and_(
                Pass.from_user_id == current_user.id,
                Pass.to_user_id == user_id
            )
        )
    )
    existing_pass = result.scalar_one_or_none()

    if existing_pass:
        # 已經跳過過，刪除舊記錄
        await db.execute(
            delete(Pass).where(
                and_(
                    Pass.from_user_id == current_user.id,
                    Pass.to_user_id == user_id
                )
            )
        )

    # 創建新記錄（時間會是當前時間）
    new_pass = Pass(
        from_user_id=current_user.id,
        to_user_id=user_id
    )
    db.add(new_pass)
    await db.commit()

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
        photos = [
            photo.url
            for photo in sorted(
                matched_profile.photos, key=lambda p: p.display_order
            )
        ]

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
