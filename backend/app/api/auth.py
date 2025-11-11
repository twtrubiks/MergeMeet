"""認證相關 API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import random
import string

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    EmailVerificationRequest,
)

router = APIRouter()

# 簡易的驗證碼儲存（生產環境應使用 Redis）
verification_codes = {}


def generate_verification_code() -> str:
    """生成 6 位數驗證碼"""
    return ''.join(random.choices(string.digits, k=6))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用戶註冊

    - 驗證年齡（必須 >= 18）
    - 檢查 Email 唯一性
    - 建立用戶帳號
    - 發送驗證碼（模擬）
    - 返回 JWT Token
    """
    # 年齡驗證
    today = date.today()
    age = relativedelta(today, request.date_of_birth).years

    if age < 18:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必須年滿 18 歲才能註冊"
        )

    # 檢查 Email 是否已註冊
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email 已被註冊"
        )

    # 建立用戶
    new_user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        date_of_birth=request.date_of_birth,
        email_verified=False,
        is_active=True,  # 明確設置為啟用狀態
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 生成驗證碼（模擬發送 Email）
    verification_code = generate_verification_code()
    verification_codes[request.email] = verification_code
    print(f"📧 [模擬] 發送驗證碼到 {request.email}: {verification_code}")

    # 生成 JWT Token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用戶登入

    - 驗證 Email 和密碼
    - 檢查帳號狀態
    - 返回 JWT Token
    """
    # 查找用戶
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # 驗證用戶存在且密碼正確
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email 或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 檢查帳號是否啟用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )

    # 檢查是否被封禁
    if user.banned_until and user.banned_until > date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"帳號已被封禁至 {user.banned_until}"
        )

    # 生成 JWT Token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    刷新 Access Token

    - 驗證 Refresh Token
    - 返回新的 Access Token 和 Refresh Token
    """
    # 解碼 Refresh Token
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Refresh Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 驗證用戶存在
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶不存在或已停用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成新的 Token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/verify-email", response_model=dict)
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    驗證 Email

    - 檢查驗證碼是否正確
    - 更新用戶的 email_verified 狀態
    """
    # 檢查驗證碼
    stored_code = verification_codes.get(request.email)

    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="找不到驗證碼，請重新註冊"
        )

    if stored_code != request.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="驗證碼錯誤"
        )

    # 更新用戶狀態
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )

    user.email_verified = True
    await db.commit()

    # 刪除已使用的驗證碼
    del verification_codes[request.email]

    return {
        "message": "Email 驗證成功",
        "email": request.email,
        "verified": True
    }


@router.post("/resend-verification", response_model=dict)
async def resend_verification(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    重新發送驗證碼

    - 檢查用戶是否存在
    - 生成新的驗證碼
    - 模擬發送 Email
    """
    # 檢查用戶
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email 已驗證"
        )

    # 生成新的驗證碼
    verification_code = generate_verification_code()
    verification_codes[email] = verification_code
    print(f"📧 [模擬] 重新發送驗證碼到 {email}: {verification_code}")

    return {
        "message": "驗證碼已重新發送",
        "email": email
    }
