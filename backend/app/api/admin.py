"""管理後台 API"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta, timezone
import re

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.core.utils import mask_email
from app.models.user import User
from app.models.match import Match, BlockedUser, Message
from app.models.report import Report
from app.schemas.admin import (
    DashboardStatsResponse,
    ReportDetailResponse,
    ReviewReportRequest,
    UserManagementResponse,
    BanUserRequest,
    UnbanUserRequest
)
from app.services.trust_score import TrustScoreService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得管理後台統計數據

    返回：
    - 用戶統計（總數、活躍、封禁）
    - 配對統計（總數、活躍）
    - 訊息統計
    - 舉報統計（總數、待處理）
    - 封鎖統計
    """
    # 用戶統計
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()

    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )
    active_users = active_users_result.scalar()

    banned_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(False))
    )
    banned_users = banned_users_result.scalar()

    # 配對統計
    total_matches_result = await db.execute(select(func.count(Match.id)))
    total_matches = total_matches_result.scalar()

    active_matches_result = await db.execute(
        select(func.count(Match.id)).where(Match.status == "ACTIVE")
    )
    active_matches = active_matches_result.scalar()

    # 訊息統計
    total_messages_result = await db.execute(select(func.count(Message.id)))
    total_messages = total_messages_result.scalar()

    # 舉報統計
    total_reports_result = await db.execute(select(func.count(Report.id)))
    total_reports = total_reports_result.scalar()

    pending_reports_result = await db.execute(
        select(func.count(Report.id)).where(Report.status == "PENDING")
    )
    pending_reports = pending_reports_result.scalar()

    # 封鎖統計
    total_blocked_result = await db.execute(select(func.count(BlockedUser.id)))
    total_blocked_users = total_blocked_result.scalar()

    return DashboardStatsResponse(
        total_users=total_users,
        active_users=active_users,
        banned_users=banned_users,
        total_matches=total_matches,
        active_matches=active_matches,
        total_messages=total_messages,
        total_reports=total_reports,
        pending_reports=pending_reports,
        total_blocked_users=total_blocked_users
    )


@router.get("/reports", response_model=List[ReportDetailResponse])
async def get_all_reports(
    status_filter: str = Query(None, description="篩選狀態: PENDING, APPROVED, REJECTED"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有舉報記錄

    支援：
    - 狀態篩選
    - 分頁
    """
    query = select(Report)

    # 狀態篩選
    if status_filter:
        query = query.where(Report.status == status_filter)

    # 排序（最新的在前）
    query = query.order_by(Report.created_at.desc())

    # 分頁
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    reports = result.scalars().all()

    if not reports:
        return []

    # 批次載入：收集所有相關用戶 ID（修復：避免 N+1 查詢）
    user_ids = set()
    for report in reports:
        user_ids.add(report.reporter_id)
        user_ids.add(report.reported_user_id)

    # 批次查詢所有用戶（1 次查詢取代 2N 次）
    users_result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users_by_id = {u.id: u for u in users_result.scalars().all()}

    # 組裝響應
    response = []
    for report in reports:
        reporter = users_by_id.get(report.reporter_id)
        reported_user = users_by_id.get(report.reported_user_id)

        if reporter and reported_user:
            response.append(ReportDetailResponse(
                id=str(report.id),
                reporter_id=str(report.reporter_id),
                reporter_email=mask_email(reporter.email),  # 脫敏處理保護隱私
                reported_user_id=str(report.reported_user_id),
                reported_user_email=mask_email(reported_user.email),  # 脫敏處理保護隱私
                report_type=report.report_type,
                reason=report.reason,
                evidence=report.evidence,
                status=report.status,
                admin_notes=report.admin_notes,
                created_at=report.created_at,
                reviewed_at=report.reviewed_at,
                reviewed_by=str(report.reviewed_by) if report.reviewed_by else None
            ))

    return response


@router.post("/reports/{report_id}/review")
async def review_report(
    report_id: str,
    request: ReviewReportRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    處理舉報

    管理員可以：
    - 批准舉報 (APPROVED)
    - 拒絕舉報 (REJECTED)
    - 標記為審查中 (UNDER_REVIEW)
    - 對被舉報用戶採取行動（警告、封禁）
    """
    # 取得舉報
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="舉報不存在"
        )

    # 更新舉報狀態
    report.status = request.status
    report.admin_notes = request.admin_notes
    report.reviewed_at = func.now()
    report.reviewed_by = current_admin.id

    # 根據處理結果採取行動
    if request.action:
        # 取得被舉報用戶
        user_result = await db.execute(
            select(User).where(User.id == report.reported_user_id)
        )
        user = user_result.scalar_one_or_none()

        if user:
            if request.action == "BAN_USER":
                user.is_active = False
                user.ban_reason = f"舉報: {report.reason}"
            elif request.action == "WARNING":
                user.warning_count += 1

    await db.commit()

    # 舉報被確認時（APPROVED），額外扣分 -10
    if request.status == "APPROVED":
        await TrustScoreService.adjust_score(
            db, report.reported_user_id, "report_confirmed"
        )
        logger.info(
            f"Trust score -10 for user {report.reported_user_id} (report_confirmed)"
        )

    return {
        "success": True,
        "message": "舉報已處理",
        "report_id": str(report.id),
        "status": report.status
    }


def escape_like_pattern(pattern: str) -> str:
    """
    轉義 SQL LIKE 模式中的特殊字符

    LIKE 特殊字符：
    - % : 匹配任意數量字符
    - _ : 匹配單個字符
    - \\ : 轉義字符本身

    Args:
        pattern: 原始搜尋字串

    Returns:
        轉義後的安全字串
    """
    # 先轉義反斜線，再轉義 % 和 _
    pattern = pattern.replace("\\", "\\\\")
    pattern = pattern.replace("%", "\\%")
    pattern = pattern.replace("_", "\\_")
    return pattern


@router.get("/users", response_model=List[UserManagementResponse])
async def get_all_users(
    search: str = Query(None, description="搜尋 email", max_length=100),
    is_active: bool = Query(None, description="篩選啟用狀態"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有用戶列表

    支援：
    - Email 搜尋（安全過濾）
    - 狀態篩選
    - 分頁
    """
    query = select(User)

    # 搜尋（修復：多層安全防護）
    if search:
        # 1. 只允許安全字符：字母、數字、@、.、-（移除 _ 因為它是 LIKE 特殊字符）
        safe_search = re.sub(r'[^\w@.\-]', '', search)
        if safe_search:
            # 2. 轉義 LIKE 特殊字符（防止 LIKE 注入）
            escaped_search = escape_like_pattern(safe_search)
            # 3. 使用參數化查詢（SQLAlchemy ORM 自動處理）
            query = query.where(User.email.ilike(f"%{escaped_search}%"))

    # 狀態篩選
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # 排序
    query = query.order_by(User.created_at.desc())

    # 分頁
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    return [
        UserManagementResponse(
            id=str(user.id),
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            trust_score=user.trust_score,  # Pydantic validator 處理 NULL
            warning_count=user.warning_count,  # Pydantic validator 處理 NULL
            ban_reason=user.ban_reason,
            banned_until=user.banned_until,
            created_at=user.created_at,
            email_verified=user.email_verified
        )
        for user in users
    ]


@router.post("/users/ban")
async def ban_user(
    request: BanUserRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    封禁用戶

    可設定封禁期限，或永久封禁
    """
    # 取得用戶
    result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )

    # 不能封禁管理員
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能封禁管理員"
        )

    # 設定封禁
    user.is_active = False
    user.ban_reason = request.reason

    if request.duration_days:
        user.banned_until = datetime.now(timezone.utc) + timedelta(days=request.duration_days)
    else:
        user.banned_until = None  # 永久封禁

    await db.commit()

    return {
        "success": True,
        "message": "用戶已被封禁",
        "user_id": str(user.id),
        "banned_until": user.banned_until.isoformat() if user.banned_until else "永久"
    }


@router.post("/users/unban")
async def unban_user(
    request: UnbanUserRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    解封用戶
    """
    # 取得用戶
    result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )

    # 解封
    user.is_active = True
    user.ban_reason = None
    user.banned_until = None

    await db.commit()

    return {
        "success": True,
        "message": "用戶已解封",
        "user_id": str(user.id)
    }
