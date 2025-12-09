"""認證相關 API

提供用戶註冊、登入、登出、Token 刷新、Email 驗證等功能。

TODO: 未實現功能（上線前建議完成）

1. 密碼重置功能（高優先級）
   - POST /forgot-password: 發送密碼重置郵件
   - POST /reset-password: 使用重置令牌設定新密碼
   - 需整合 Email 發送服務
   - 重置 Token 建議 1 小時過期
   - 風險：用戶忘記密碼無法恢復帳號

2. 登入失敗次數限制（高優先級）
   - 目前登入端點無失敗次數限制
   - 建議：5 次失敗後鎖定帳戶 15 分鐘
   - 可使用 Redis 或內存字典實現
   - 風險：密碼暴力破解攻擊
   - 影響端點：/login, /admin-login

3. 密碼修改功能（中優先級）
   - POST /change-password: 修改密碼（需舊密碼驗證）
   - 建議：禁止使用最近 3 次的密碼（密碼歷史檢查）
   - 風險：用戶無法主動修改密碼
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import random
import string
import asyncio
import logging
from typing import Dict, Tuple, Optional

from app.core.database import get_db


def mask_email(email: str) -> str:
    """
    Email 脫敏處理，保護用戶隱私

    示例:
    - user@example.com -> us***@example.com
    - a@test.com -> a***@test.com
    - longname@domain.com -> lo***e@domain.com

    Args:
        email: 原始 email 地址

    Returns:
        脫敏後的 email 地址
    """
    if not email or '@' not in email:
        return '***@***'

    local, domain = email.split('@', 1)

    if len(local) <= 1:
        masked_local = local[0] + '***'
    elif len(local) <= 3:
        masked_local = local[0] + '***'
    else:
        # 保留前兩個和最後一個字符，中間替換為 ***
        masked_local = local[:2] + '***' + local[-1]

    return f"{masked_local}@{domain}"
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    EmailVerificationRequest,
)
from app.services.token_blacklist import token_blacklist

router = APIRouter()
logger = logging.getLogger(__name__)


def _generate_auth_tokens(user_id: str) -> Tuple[str, str]:
    """生成認證 token (access + refresh)

    Args:
        user_id: 用戶 ID (字串格式)

    Returns:
        Tuple[str, str]: (access_token, refresh_token)
    """
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    return access_token, refresh_token


class VerificationCodeStore:
    """帶過期機制的驗證碼存儲

    Redis 整合備註（暫未使用）：
    - 生產環境建議使用 Redis: redis.setex(f"verify:{email}", 600, code)
    - 支援多實例部署時的驗證碼共享
    - 天然支援 TTL 自動過期
    """

    def __init__(self, ttl_minutes: int = 10):
        self._store: Dict[str, Tuple[str, datetime]] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(minutes=ttl_minutes)

    async def set(self, email: str, code: str) -> None:
        """設置驗證碼，帶過期時間"""
        async with self._lock:
            expires_at = datetime.now(timezone.utc) + self._ttl
            self._store[email] = (code, expires_at)

    async def get(self, email: str) -> Optional[str]:
        """獲取驗證碼，自動檢查過期"""
        async with self._lock:
            if email not in self._store:
                return None

            code, expires_at = self._store[email]

            # 檢查是否過期
            if datetime.now(timezone.utc) > expires_at:
                del self._store[email]
                return None

            return code

    async def delete(self, email: str) -> None:
        """刪除驗證碼"""
        async with self._lock:
            self._store.pop(email, None)

    async def cleanup_expired(self) -> int:
        """清理過期的驗證碼，返回清理數量"""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = [
                email for email, (_, expires_at) in self._store.items()
                if now > expires_at
            ]

            for email in expired_keys:
                del self._store[email]

            return len(expired_keys)


# 驗證碼儲存（10 分鐘過期）
# 注意：目前 Email 發送服務尚未整合，驗證碼會記錄在後端 log 中
# 開發測試時請查看 uvicorn 終端輸出，搜尋 "📧 [模擬] 發送驗證碼" 取得驗證碼
verification_codes = VerificationCodeStore(ttl_minutes=10)

# Email 發送速率限制（防止濫用）
# 格式: {email: (last_sent_time, send_count_today)}
email_rate_limit: Dict[str, Tuple[datetime, int]] = {}
email_rate_limit_lock = asyncio.Lock()


async def check_email_rate_limit(email: str) -> bool:
    """
    檢查 Email 發送速率限制

    規則:
    - 60 秒內只能發送 1 次
    - 每天最多發送 5 次

    Returns:
        True 如果允許發送，False 如果超過限制

    Raises:
        HTTPException 如果超過限制
    """
    async with email_rate_limit_lock:
        now = datetime.now(timezone.utc)

        if email in email_rate_limit:
            last_sent, count_today = email_rate_limit[email]

            # 檢查是否在 60 秒冷卻期內
            time_since_last = (now - last_sent).total_seconds()
            if time_since_last < 60:
                remaining = 60 - int(time_since_last)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"發送過於頻繁，請等待 {remaining} 秒後再試"
                )

            # 檢查是否是新的一天（重置計數）
            if last_sent.date() < now.date():
                email_rate_limit[email] = (now, 1)
            else:
                # 同一天，檢查次數限制
                if count_today >= 5:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="今日發送次數已達上限（5 次），請明天再試"
                    )
                email_rate_limit[email] = (now, count_today + 1)
        else:
            # 第一次發送
            email_rate_limit[email] = (now, 1)

        return True


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
        # 防止用戶枚舉：不透露 Email 是否已註冊
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="註冊失敗，請檢查輸入資料"  # 模糊訊息
        )

    # 建立用戶（修復：使用資料庫唯一約束處理並發註冊）
    new_user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        date_of_birth=request.date_of_birth,
        email_verified=False,
        is_active=True,  # 明確設置為啟用狀態
    )

    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        # 並發情況下，另一個請求已創建了同樣的用戶
        await db.rollback()
        logger.warning(f"Concurrent registration attempt for email: {mask_email(request.email)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="註冊失敗，請檢查輸入資料"
        )

    # 生成驗證碼
    # TODO: 整合 Email 發送服務（如 SendGrid、AWS SES）後移除模擬邏輯
    # 暫時不會發信，開發測試時可從日誌查看驗證碼（安全起見已註解）
    verification_code = generate_verification_code()
    await verification_codes.set(request.email, verification_code)
    # 開發環境可取消註解以查看驗證碼（生產環境禁止）
    # logger.info(f"📧 [開發] 驗證碼: {verification_code} (Email: {mask_email(request.email)})")
    logger.info(f"Verification code sent to {mask_email(request.email)}")

    # 生成 JWT Token
    access_token, refresh_token = _generate_auth_tokens(str(new_user.id))

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

    # 檢查是否被封禁（修復：使用 datetime 而非 date）
    if user.banned_until and user.banned_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"帳號已被封禁至 {user.banned_until}"
        )

    # 生成 JWT Token
    access_token, refresh_token = _generate_auth_tokens(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/admin-login", response_model=TokenResponse)
async def admin_login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    管理員登入

    - 驗證 Email 和密碼
    - 檢查管理員權限
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

    # 檢查是否為管理員
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="沒有管理員權限"
        )

    # 檢查帳號是否啟用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )

    # 檢查是否被封禁（修復：使用 datetime 而非 date）
    if user.banned_until and user.banned_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"帳號已被封禁至 {user.banned_until}"
        )

    # 生成 JWT Token
    access_token, refresh_token = _generate_auth_tokens(str(user.id))

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
    access_token, refresh_token = _generate_auth_tokens(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=dict)
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """
    用戶登出

    - 將當前 Token 加入黑名單
    - Token 在過期前都無法再使用
    - 同時使 WebSocket 連接失效
    """
    token = credentials.credentials

    # 解碼 Token 取得過期時間
    payload = decode_token(token)
    if payload and payload.get("exp"):
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    else:
        # 如果無法取得過期時間，使用預設的 access token 過期時間
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # 將 Token 加入黑名單
    await token_blacklist.add(token, expires_at)

    logger.info(f"User {current_user.id} logged out, token blacklisted")

    return {
        "message": "登出成功",
        "user_id": str(current_user.id)
    }


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
    stored_code = await verification_codes.get(request.email)

    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="驗證碼不存在或已過期（10分鐘有效期），請重新發送"
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
    await verification_codes.delete(request.email)

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

    - 檢查速率限制（60 秒冷卻 + 每日 5 次限制）
    - 檢查用戶是否存在
    - 生成新的驗證碼
    - 模擬發送 Email
    """
    # 檢查速率限制（會自動拋出 HTTPException 如果超過限制）
    await check_email_rate_limit(email)

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
    # TODO: 整合 Email 發送服務後移除模擬邏輯
    # 暫時不會發信，開發測試時可從日誌查看驗證碼（安全起見已註解）
    verification_code = generate_verification_code()
    await verification_codes.set(email, verification_code)
    # 開發環境可取消註解以查看驗證碼（生產環境禁止）
    # logger.info(f"📧 [開發] 驗證碼: {verification_code} (Email: {mask_email(email)})")
    logger.info(f"Verification code resent to {mask_email(email)}")

    return {
        "message": "驗證碼已重新發送",
        "email": email
    }
