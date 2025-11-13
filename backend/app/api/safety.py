"""安全功能 API - 封鎖與舉報"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.match import BlockedUser, Match
from app.schemas.safety import (
    BlockUserRequest,
    BlockedUserResponse,
    UnblockUserRequest,
)

router = APIRouter()


@router.post("/block/{user_id}", status_code=status.HTTP_201_CREATED)
async def block_user(
    user_id: str,
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
    if str(current_user.id) == user_id:
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
        blocked_id=uuid.UUID(user_id),
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
        match.unmatched_at = datetime.utcnow()
        match.unmatched_by = current_user.id

    await db.commit()

    return {
        "blocked": True,
        "message": "已封鎖用戶",
        "match_cancelled": match is not None
    }


@router.delete("/block/{user_id}")
async def unblock_user(
    user_id: str,
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
    """取得封鎖列表"""
    result = await db.execute(
        select(BlockedUser)
        .where(BlockedUser.blocker_id == current_user.id)
        .order_by(BlockedUser.created_at.desc())
    )
    blocked_users = result.scalars().all()

    # 取得被封鎖用戶的資訊
    response = []
    for block in blocked_users:
        user_result = await db.execute(
            select(User).where(User.id == block.blocked_id)
        )
        user = user_result.scalar_one_or_none()

        if user:
            response.append(BlockedUserResponse(
                id=str(block.id),
                blocked_user_id=str(user.id),
                blocked_user_email=user.email,
                reason=block.reason,
                created_at=block.created_at
            ))

    return response
