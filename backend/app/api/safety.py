"""安全功能 API - 封鎖與舉報"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.match import BlockedUser, Match
from app.models.report import Report
from app.schemas.safety import (
    BlockUserRequest,
    BlockedUserResponse,
    UnblockUserRequest,
    ReportUserRequest,
    ReportResponse,
)

router = APIRouter()


@router.post("/block/{user_id}", status_code=status.HTTP_201_CREATED)
async def block_user(
    user_id: uuid.UUID,
    request: BlockUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    封鎖用戶

    - 封鎖後自動取消配對
    - 被封鎖用戶不會出現在探索頁面
    - 不能封鎖自己
    """
    # 驗證不能封鎖自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無法封鎖自己"
        )

    # 檢查用戶是否存在
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )

    # 檢查是否已經封鎖
    result = await db.execute(
        select(BlockedUser).where(
            and_(
                BlockedUser.blocker_id == current_user.id,
                BlockedUser.blocked_id == user_id
            )
        )
    )
    existing_block = result.scalar_one_or_none()

    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已經封鎖此用戶"
        )

    # 創建封鎖記錄
    new_block = BlockedUser(
        blocker_id=current_user.id,
        blocked_id=user_id,
        reason=request.reason
    )
    db.add(new_block)

    # 如果有配對，自動取消
    result = await db.execute(
        select(Match).where(
            and_(
                Match.status == "ACTIVE",
                or_(
                    and_(Match.user1_id == current_user.id, Match.user2_id == user_id),
                    and_(Match.user1_id == user_id, Match.user2_id == current_user.id)
                )
            )
        )
    )
    match = result.scalar_one_or_none()

    if match:
        match.status = "UNMATCHED"
        match.unmatched_at = func.now()
        match.unmatched_by = current_user.id

    await db.commit()

    return {
        "blocked": True,
        "message": "已封鎖用戶",
        "match_cancelled": match is not None
    }


@router.delete("/block/{user_id}")
async def unblock_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """解除封鎖用戶"""
    # 查找封鎖記錄
    result = await db.execute(
        select(BlockedUser).where(
            and_(
                BlockedUser.blocker_id == current_user.id,
                BlockedUser.blocked_id == user_id
            )
        )
    )
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未封鎖此用戶"
        )

    await db.delete(block)
    await db.commit()

    return {
        "unblocked": True,
        "message": "已解除封鎖"
    }


@router.get("/blocked", response_model=List[BlockedUserResponse])
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得封鎖列表

    優化：批次載入用戶資訊，避免 N+1 查詢問題
    """
    result = await db.execute(
        select(BlockedUser)
        .where(BlockedUser.blocker_id == current_user.id)
        .order_by(BlockedUser.created_at.desc())
    )
    blocked_users = result.scalars().all()

    if not blocked_users:
        return []

    # 批次載入：收集所有被封鎖用戶 ID
    blocked_user_ids = [block.blocked_id for block in blocked_users]

    # 批次查詢所有被封鎖的用戶（1 次查詢取代 N 次）
    users_result = await db.execute(
        select(User).where(User.id.in_(blocked_user_ids))
    )
    users_by_id = {u.id: u for u in users_result.scalars().all()}

    # 組裝回應
    response = []
    for block in blocked_users:
        user = users_by_id.get(block.blocked_id)
        if user:
            response.append(BlockedUserResponse(
                id=str(block.id),
                blocked_user_id=str(user.id),
                blocked_user_email=user.email,
                reason=block.reason,
                created_at=block.created_at
            ))

    return response


@router.post("/report", status_code=status.HTTP_201_CREATED, response_model=ReportResponse)
async def report_user(
    request: ReportUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    舉報用戶

    - 可舉報不當行為、騷擾、假帳號、詐騙等
    - 不能舉報自己
    - 需提供舉報原因（至少 10 字）
    """
    # 在函數開頭統一轉換和驗證用戶 ID 格式
    try:
        reported_user_uuid = uuid.UUID(request.reported_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的用戶 ID 格式"
        )

    # 驗證不能舉報自己（使用統一的 UUID 類型）
    if current_user.id == reported_user_uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無法舉報自己"
        )

    # 檢查被舉報用戶是否存在（使用統一的 UUID 類型）
    result = await db.execute(
        select(User).where(User.id == reported_user_uuid)
    )
    reported_user = result.scalar_one_or_none()

    if not reported_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="被舉報用戶不存在"
        )

    # 驗證舉報類型
    valid_types = ["INAPPROPRIATE", "HARASSMENT", "FAKE", "SCAM", "OTHER"]
    if request.report_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無效的舉報類型。有效類型：{', '.join(valid_types)}"
        )

    # 創建舉報記錄（使用統一的 UUID 對象）
    new_report = Report(
        reporter_id=current_user.id,
        reported_user_id=reported_user_uuid,
        report_type=request.report_type,
        reason=request.reason,
        evidence=request.evidence,
        status="PENDING"
    )
    db.add(new_report)

    # 更新被舉報用戶的警告次數
    reported_user.warning_count += 1

    await db.commit()
    await db.refresh(new_report)

    return ReportResponse(
        id=str(new_report.id),
        reported_user_id=str(new_report.reported_user_id),
        report_type=new_report.report_type,
        reason=new_report.reason,
        status=new_report.status,
        created_at=new_report.created_at
    )


@router.get("/reports", response_model=List[ReportResponse])
async def get_my_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取得我的舉報記錄"""
    result = await db.execute(
        select(Report)
        .where(Report.reporter_id == current_user.id)
        .order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()

    return [
        ReportResponse(
            id=str(report.id),
            reported_user_id=str(report.reported_user_id),
            report_type=report.report_type,
            reason=report.reason,
            status=report.status,
            created_at=report.created_at
        )
        for report in reports
    ]
