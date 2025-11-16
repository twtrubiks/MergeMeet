"""管理後台 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.models.match import Match, BlockedUser
from app.models.profile import Profile
from app.models.report import Report
from app.schemas.admin import (
    DashboardStatsResponse,
    ReportDetailResponse,
    ReviewReportRequest,
    UserManagementResponse,
    BanUserRequest,
    UnbanUserRequest
)

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
    from app.models.match import Message

    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()

    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users_result.scalar()

    banned_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == False)
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

    # 組裝響應
    response = []
    for report in reports:
        # 取得舉報者資訊
        reporter_result = await db.execute(
            select(User).where(User.id == report.reporter_id)
        )
        reporter = reporter_result.scalar_one_or_none()

        # 取得被舉報者資訊
        reported_result = await db.execute(
            select(User).where(User.id == report.reported_user_id)
        )
        reported_user = reported_result.scalar_one_or_none()

        if reporter and reported_user:
            response.append(ReportDetailResponse(
                id=str(report.id),
                reporter_id=str(report.reporter_id),
                reporter_email=reporter.email,
                reported_user_id=str(report.reported_user_id),
                reported_user_email=reported_user.email,
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
                user.trust_score = max(0, user.trust_score - 10)

    await db.commit()

    return {
        "success": True,
        "message": "舉報已處理",
        "report_id": str(report.id),
        "status": report.status
    }


@router.get("/users", response_model=List[UserManagementResponse])
async def get_all_users(
    search: str = Query(None, description="搜尋 email"),
    is_active: bool = Query(None, description="篩選啟用狀態"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有用戶列表

    支援：
    - Email 搜尋
    - 狀態篩選
    - 分頁
    """
    query = select(User)

    # 搜尋
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))

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
            trust_score=user.trust_score,
            warning_count=user.warning_count,
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
        from datetime import datetime, timezone
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
