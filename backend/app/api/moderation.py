"""內容審核管理 API - 敏感詞管理和申訴處理"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user, get_current_user
from app.models.user import User
from app.models.moderation import SensitiveWord, ContentAppeal, ModerationLog
from app.services.content_moderation import ContentModerationService
from app.schemas.moderation import (
    SensitiveWordCreate,
    SensitiveWordUpdate,
    SensitiveWordResponse,
    SensitiveWordListResponse,
    ContentAppealCreate,
    ContentAppealReview,
    ContentAppealResponse,
    ContentAppealListResponse,
    ModerationLogResponse,
    ModerationLogListResponse,
    ModerationStatsResponse
)

router = APIRouter()


# ============ 敏感詞管理 API（管理員專用）============

@router.get("/sensitive-words", response_model=SensitiveWordListResponse)
async def get_sensitive_words(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得敏感詞列表（管理員）

    Query 參數：
    - category: 篩選分類（可選）
    - is_active: 篩選啟用狀態（可選）
    - page: 頁碼
    - page_size: 每頁數量
    """
    query = select(SensitiveWord)

    # 篩選條件
    if category:
        query = query.where(SensitiveWord.category == category)
    if is_active is not None:
        query = query.where(SensitiveWord.is_active == is_active)

    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分頁查詢
    query = query.order_by(desc(SensitiveWord.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    words = result.scalars().all()

    return SensitiveWordListResponse(
        words=[SensitiveWordResponse.model_validate(word) for word in words],
        total=total
    )


@router.post("/sensitive-words", response_model=SensitiveWordResponse, status_code=status.HTTP_201_CREATED)
async def create_sensitive_word(
    word_data: SensitiveWordCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    新增敏感詞（管理員）
    """
    # 檢查是否已存在
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.word == word_data.word.lower())
    )
    existing_word = result.scalar_one_or_none()

    if existing_word:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"敏感詞 '{word_data.word}' 已存在"
        )

    # 創建新敏感詞
    new_word = SensitiveWord(
        word=word_data.word.lower(),
        category=word_data.category,
        severity=word_data.severity,
        action=word_data.action,
        is_regex=word_data.is_regex,
        description=word_data.description,
        created_by=current_admin.id
    )

    db.add(new_word)
    await db.commit()
    await db.refresh(new_word)

    # 清除快取
    ContentModerationService.clear_cache()

    return SensitiveWordResponse.model_validate(new_word)


@router.get("/sensitive-words/{word_id}", response_model=SensitiveWordResponse)
async def get_sensitive_word(
    word_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得單一敏感詞詳情（管理員）
    """
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.id == word_id)
    )
    word = result.scalar_one_or_none()

    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="敏感詞不存在"
        )

    return SensitiveWordResponse.model_validate(word)


@router.patch("/sensitive-words/{word_id}", response_model=SensitiveWordResponse)
async def update_sensitive_word(
    word_id: uuid.UUID,
    word_data: SensitiveWordUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新敏感詞（管理員）
    """
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.id == word_id)
    )
    word = result.scalar_one_or_none()

    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="敏感詞不存在"
        )

    # 更新欄位
    update_data = word_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(word, field, value)

    word.updated_at = datetime.now()

    await db.commit()
    await db.refresh(word)

    # 清除快取
    ContentModerationService.clear_cache()

    return SensitiveWordResponse.model_validate(word)


@router.delete("/sensitive-words/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensitive_word(
    word_id: uuid.UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除敏感詞（管理員）

    注意：這是軟刪除，實際上是將 is_active 設為 False
    """
    result = await db.execute(
        select(SensitiveWord).where(SensitiveWord.id == word_id)
    )
    word = result.scalar_one_or_none()

    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="敏感詞不存在"
        )

    # 軟刪除
    word.is_active = False
    word.updated_at = datetime.now()

    await db.commit()

    # 清除快取
    ContentModerationService.clear_cache()


# ============ 內容申訴 API ============

@router.post("/appeals", response_model=ContentAppealResponse, status_code=status.HTTP_201_CREATED)
async def create_appeal(
    appeal_data: ContentAppealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    提交內容申訴（一般用戶）
    """
    # 創建申訴
    appeal = ContentAppeal(
        user_id=current_user.id,
        appeal_type=appeal_data.appeal_type,
        rejected_content=appeal_data.rejected_content,
        violations=appeal_data.violations,
        reason=appeal_data.reason
    )

    db.add(appeal)
    await db.commit()
    await db.refresh(appeal)

    return ContentAppealResponse.model_validate(appeal)


@router.get("/appeals/my", response_model=ContentAppealListResponse)
async def get_my_appeals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得我的申訴列表（一般用戶）
    """
    # 計算總數
    count_result = await db.execute(
        select(func.count(ContentAppeal.id)).where(
            ContentAppeal.user_id == current_user.id
        )
    )
    total = count_result.scalar()

    # 分頁查詢
    query = (
        select(ContentAppeal)
        .where(ContentAppeal.user_id == current_user.id)
        .order_by(desc(ContentAppeal.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    appeals = result.scalars().all()

    return ContentAppealListResponse(
        appeals=[ContentAppealResponse.model_validate(appeal) for appeal in appeals],
        total=total
    )


@router.get("/appeals", response_model=ContentAppealListResponse)
async def get_all_appeals(
    status_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有申訴列表（管理員）
    """
    query = select(ContentAppeal)

    # 篩選狀態
    if status_filter:
        query = query.where(ContentAppeal.status == status_filter)

    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分頁查詢
    query = query.order_by(desc(ContentAppeal.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    appeals = result.scalars().all()

    return ContentAppealListResponse(
        appeals=[ContentAppealResponse.model_validate(appeal) for appeal in appeals],
        total=total
    )


@router.post("/appeals/{appeal_id}/review")
async def review_appeal(
    appeal_id: uuid.UUID,
    review_data: ContentAppealReview,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    審核申訴（管理員）
    """
    result = await db.execute(
        select(ContentAppeal).where(ContentAppeal.id == appeal_id)
    )
    appeal = result.scalar_one_or_none()

    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申訴不存在"
        )

    if appeal.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此申訴已被處理"
        )

    # 更新申訴狀態
    appeal.status = review_data.status
    appeal.admin_response = review_data.admin_response
    appeal.reviewed_by = current_admin.id
    appeal.reviewed_at = datetime.now()
    appeal.updated_at = datetime.now()

    await db.commit()
    await db.refresh(appeal)

    return ContentAppealResponse.model_validate(appeal)


# ============ 審核日誌 API（管理員）============

@router.get("/logs", response_model=ModerationLogListResponse)
async def get_moderation_logs(
    user_id: Optional[uuid.UUID] = None,
    content_type: Optional[str] = None,
    is_approved: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得審核日誌（管理員）
    """
    query = select(ModerationLog)

    # 篩選條件
    if user_id:
        query = query.where(ModerationLog.user_id == user_id)
    if content_type:
        query = query.where(ModerationLog.content_type == content_type)
    if is_approved is not None:
        query = query.where(ModerationLog.is_approved == is_approved)
    if start_date:
        query = query.where(ModerationLog.created_at >= start_date)
    if end_date:
        query = query.where(ModerationLog.created_at <= end_date)

    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分頁查詢
    query = query.order_by(desc(ModerationLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return ModerationLogListResponse(
        logs=[ModerationLogResponse.model_validate(log) for log in logs],
        total=total
    )


# ============ 審核統計 API（管理員）============

@router.get("/stats", response_model=ModerationStatsResponse)
async def get_moderation_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得審核統計數據（管理員）
    """
    # 敏感詞統計
    total_words_result = await db.execute(select(func.count(SensitiveWord.id)))
    total_sensitive_words = total_words_result.scalar()

    active_words_result = await db.execute(
        select(func.count(SensitiveWord.id)).where(SensitiveWord.is_active == True)
    )
    active_sensitive_words = active_words_result.scalar()

    # 申訴統計
    total_appeals_result = await db.execute(select(func.count(ContentAppeal.id)))
    total_appeals = total_appeals_result.scalar()

    pending_appeals_result = await db.execute(
        select(func.count(ContentAppeal.id)).where(ContentAppeal.status == "PENDING")
    )
    pending_appeals = pending_appeals_result.scalar()

    approved_appeals_result = await db.execute(
        select(func.count(ContentAppeal.id)).where(ContentAppeal.status == "APPROVED")
    )
    approved_appeals = approved_appeals_result.scalar()

    rejected_appeals_result = await db.execute(
        select(func.count(ContentAppeal.id)).where(ContentAppeal.status == "REJECTED")
    )
    rejected_appeals = rejected_appeals_result.scalar()

    # 違規統計
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    today_violations_result = await db.execute(
        select(func.count(ModerationLog.id)).where(
            and_(
                ModerationLog.is_approved == False,
                ModerationLog.created_at >= today_start
            )
        )
    )
    total_violations_today = today_violations_result.scalar()

    week_violations_result = await db.execute(
        select(func.count(ModerationLog.id)).where(
            and_(
                ModerationLog.is_approved == False,
                ModerationLog.created_at >= week_start
            )
        )
    )
    total_violations_this_week = week_violations_result.scalar()

    month_violations_result = await db.execute(
        select(func.count(ModerationLog.id)).where(
            and_(
                ModerationLog.is_approved == False,
                ModerationLog.created_at >= month_start
            )
        )
    )
    total_violations_this_month = month_violations_result.scalar()

    # 最常觸發的敏感詞（簡化版，返回空列表）
    # 實際應該分析 triggered_word_ids 欄位
    most_triggered_words = []

    return ModerationStatsResponse(
        total_sensitive_words=total_sensitive_words,
        active_sensitive_words=active_sensitive_words,
        total_appeals=total_appeals,
        pending_appeals=pending_appeals,
        approved_appeals=approved_appeals,
        rejected_appeals=rejected_appeals,
        total_violations_today=total_violations_today,
        total_violations_this_week=total_violations_this_week,
        total_violations_this_month=total_violations_this_month,
        most_triggered_words=most_triggered_words
    )
