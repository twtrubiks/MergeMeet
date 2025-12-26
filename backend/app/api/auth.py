"""認證相關 API

提供用戶註冊、登入、登出、Token 刷新、Email 驗證等功能。

已實現功能:
- ✅ 登入失敗次數限制：5 次失敗後鎖定 15 分鐘（使用 Redis）
- ✅ 密碼重置功能：發送郵件 + 重置 Token
- ✅ 密碼修改功能：POST /change-password（需舊密碼驗證，修改後 Token 失效）
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
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
from app.core.utils import mask_email
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.cookie_utils import set_auth_cookies, clear_auth_cookies, generate_csrf_token
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    EmailVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyResetTokenResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
)
from app.services.token_blacklist import token_blacklist
from app.services.email import EmailService
from app.services.redis_client import get_redis
from app.services.login_limiter import LoginLimiter
from app.services.trust_score import TrustScoreService
import redis.asyncio as aioredis
import secrets

router = APIRouter()
logger = logging.getLogger(__name__)


def _generate_auth_tokens(
    user_id: str,
    email: Optional[str] = None,
    email_verified: Optional[bool] = None,
    is_admin: Optional[bool] = None
) -> Tuple[str, str]:
    """生成認證 token (access + refresh)

    Args:
        user_id: 用戶 ID (字串格式)
        email: 用戶 Email (可選)
        email_verified: Email 是否已驗證 (可選)
        is_admin: 是否為管理員 (可選)

    Returns:
        Tuple[str, str]: (access_token, refresh_token)
    """
    token_data = {"sub": user_id}
    if email is not None:
        token_data["email"] = email
    if email_verified is not None:
        token_data["email_verified"] = email_verified
    if is_admin is not None:
        token_data["is_admin"] = is_admin

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": user_id})
    return access_token, refresh_token


class VerificationCodeStore:
    """帶過期機制的驗證碼存儲

    支援 Redis 存儲（優先）和內存回退。
    當 Redis 不可用時，自動回退到內存存儲並記錄警告。

    Redis Key 設計：
    - verify:{email} - 驗證碼 (value: 6 位數碼, TTL: 600 秒)
    """

    def __init__(self, ttl_minutes: int = 10, redis_client: Optional[aioredis.Redis] = None):
        """初始化驗證碼存儲

        Args:
            ttl_minutes: 驗證碼過期時間（分鐘）
            redis_client: Redis 連線（可選，不提供時使用純內存模式）
        """
        self._redis: Optional[aioredis.Redis] = redis_client
        self._use_redis: bool = redis_client is not None
        # 內存回退存儲: email -> (code, expires_at)
        self._fallback: Dict[str, Tuple[str, datetime]] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(minutes=ttl_minutes)
        self._ttl_seconds = ttl_minutes * 60

    async def set_redis(self, redis_client: aioredis.Redis) -> None:
        """設置或更新 Redis 連線

        Args:
            redis_client: Redis 連線
        """
        self._redis = redis_client
        self._use_redis = True
        logger.info("VerificationCodeStore Redis connection configured")

    async def set(self, email: str, code: str) -> None:
        """設置驗證碼，帶過期時間

        Args:
            email: 用戶 Email
            code: 6 位數驗證碼
        """
        key = f"verify:{email.lower()}"

        # 嘗試 Redis
        if self._redis and self._use_redis:
            try:
                await self._redis.setex(key, self._ttl_seconds, code)
                logger.debug(f"Verification code stored in Redis for {email}")
                return
            except aioredis.RedisError as e:
                logger.warning(
                    f"Redis unavailable for verification code, "
                    f"falling back to memory: {e}"
                )
                self._use_redis = False

        # 內存回退
        async with self._lock:
            expires_at = datetime.now(timezone.utc) + self._ttl
            self._fallback[email.lower()] = (code, expires_at)
            logger.debug(f"Verification code stored in memory (fallback) for {email}")

    async def get(self, email: str) -> Optional[str]:
        """獲取驗證碼，自動檢查過期

        Args:
            email: 用戶 Email

        Returns:
            驗證碼，如果不存在或已過期返回 None
        """
        key = f"verify:{email.lower()}"

        # 嘗試 Redis
        if self._redis and self._use_redis:
            try:
                return await self._redis.get(key)
            except aioredis.RedisError as e:
                logger.warning(
                    f"Redis unavailable for verification code get, "
                    f"falling back to memory: {e}"
                )
                self._use_redis = False

        # 內存回退
        async with self._lock:
            email_lower = email.lower()
            if email_lower not in self._fallback:
                return None

            code, expires_at = self._fallback[email_lower]

            # 檢查是否過期
            if datetime.now(timezone.utc) > expires_at:
                del self._fallback[email_lower]
                return None

            return code

    async def delete(self, email: str) -> None:
        """刪除驗證碼

        Args:
            email: 用戶 Email
        """
        key = f"verify:{email.lower()}"

        # 嘗試從 Redis 刪除
        if self._redis and self._use_redis:
            try:
                await self._redis.delete(key)
            except aioredis.RedisError as e:
                logger.warning(f"Redis unavailable for verification code delete: {e}")

        # 同時從內存刪除
        async with self._lock:
            self._fallback.pop(email.lower(), None)

    async def cleanup_expired(self) -> int:
        """清理過期的內存驗證碼（Redis 有自動 TTL）

        Returns:
            清理的驗證碼數量
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = [
                email for email, (_, expires_at) in self._fallback.items()
                if now > expires_at
            ]

            for email in expired_keys:
                del self._fallback[email]

            if expired_keys:
                logger.info(
                    f"Cleaned up {len(expired_keys)} expired verification codes "
                    f"from memory"
                )

            return len(expired_keys)

    def is_using_redis(self) -> bool:
        """檢查是否正在使用 Redis

        Returns:
            bool: True 如果使用 Redis，False 如果使用內存回退
        """
        return self._use_redis and self._redis is not None


# 驗證碼儲存（10 分鐘過期）
# 初始無 Redis，在 main.py lifespan 中設置
verification_codes = VerificationCodeStore(ttl_minutes=10)

# Email 發送速率限制（防止濫用）
# 格式: {email: (last_sent_time, send_count_today)}
#
# TODO [Redis 擴展] 多實例部署時需改用 Redis
# 目前使用內存存儲，僅支援單實例部署。
# 如需水平擴展，建議改用 Redis 實現：
#
# Redis Key 設計：
# - email_rate:{email}:last_sent - 上次發送時間戳 (Unix timestamp)
# - email_rate:{email}:count - 今日發送次數 (integer, TTL: 到午夜)
#
# 實現參考：
# class EmailRateLimiter:
#     async def check_and_record(self, email: str) -> bool:
#         key_last = f"email_rate:{email}:last_sent"
#         key_count = f"email_rate:{email}:count"
#         # 使用 Redis MULTI/EXEC 確保原子性
#         # ...
#
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
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    用戶註冊（支援 HttpOnly Cookie + Bearer Token 雙模式）

    - 驗證年齡（必須 >= 18）
    - 檢查 Email 唯一性
    - 建立用戶帳號
    - 發送驗證碼
    - 設置 HttpOnly Cookie（Web 前端 XSS 防護）
    - 同時返回 JWT Token（API 客戶端 / 移動端）
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

    # 生成驗證碼並發送 Email
    verification_code = generate_verification_code()
    await verification_codes.set(request.email, verification_code)

    # 發送驗證郵件
    username = request.email.split('@')[0]
    email_sent = await EmailService.send_verification_email(
        to_email=request.email,
        username=username,
        verification_code=verification_code
    )

    if email_sent:
        logger.info(f"Verification email sent to {mask_email(request.email)}")
    else:
        logger.error(f"Failed to send verification email to {mask_email(request.email)}")

    # 生成 JWT Token（包含 email 資訊供前端使用）
    access_token, refresh_token = _generate_auth_tokens(
        str(new_user.id),
        email=new_user.email,
        email_verified=new_user.email_verified
    )

    # 生成 CSRF Token 並設置 Cookie（HttpOnly Cookie 模式）
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, access_token, refresh_token, csrf_token)

    # 同時返回 Token（向後兼容 Bearer Token 模式）
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis)
):
    """
    用戶登入（支援 HttpOnly Cookie + Bearer Token 雙模式）

    - 驗證 Email 和密碼
    - 檢查帳號狀態
    - 登入失敗限制：5 次失敗後鎖定 15 分鐘
    - 設置 HttpOnly Cookie（Web 前端 XSS 防護）
    - 同時返回 JWT Token（API 客戶端 / 移動端）

    Response Headers:
        X-RateLimit-Remaining: 剩餘嘗試次數
        X-Lockout-Seconds: 鎖定剩餘秒數（鎖定時）

    Cookie 設置:
        access_token: HttpOnly Cookie
        refresh_token: HttpOnly Cookie（限 /api/auth 路徑）
        csrf_token: 非 HttpOnly（前端需讀取放入 Header）
    """
    limiter = LoginLimiter(redis_conn)

    # 檢查是否被鎖定
    limit_status = await limiter.check_status(request.email)
    if limit_status.is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登入嘗試次數過多，帳號已暫時鎖定",
            headers={
                "X-RateLimit-Remaining": "0",
                "X-Lockout-Seconds": str(limit_status.lockout_seconds)
            }
        )

    # 查找用戶
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # 驗證用戶存在且密碼正確
    if not user or not verify_password(request.password, user.password_hash):
        # 記錄失敗並獲取更新狀態
        attempt_result = await limiter.record_failure(request.email)

        # 根據是否觸發鎖定決定狀態碼
        if attempt_result.is_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="登入嘗試次數過多，帳號已暫時鎖定",
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-Lockout-Seconds": str(attempt_result.lockout_seconds)
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email 或密碼錯誤",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-RateLimit-Remaining": str(attempt_result.remaining_attempts),
                    "X-Lockout-Seconds": "0"
                }
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

    # 登入成功，清除失敗記錄
    await limiter.clear_attempts(request.email)

    # 生成 JWT Token（包含 email 資訊供前端使用）
    access_token, refresh_token = _generate_auth_tokens(
        str(user.id),
        email=user.email,
        email_verified=user.email_verified
    )

    # 生成 CSRF Token 並設置 Cookie（HttpOnly Cookie 模式）
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, access_token, refresh_token, csrf_token)

    # 同時返回 Token（向後兼容 Bearer Token 模式）
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/admin-login", response_model=TokenResponse)
async def admin_login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_conn: aioredis.Redis = Depends(get_redis)
):
    """
    管理員登入（支援 HttpOnly Cookie + Bearer Token 雙模式）

    - 驗證 Email 和密碼
    - 檢查管理員權限
    - 登入失敗限制：5 次失敗後鎖定 15 分鐘
    - 設置 HttpOnly Cookie（Web 前端 XSS 防護）
    - 同時返回 JWT Token（API 客戶端 / 移動端）

    Response Headers:
        X-RateLimit-Remaining: 剩餘嘗試次數
        X-Lockout-Seconds: 鎖定剩餘秒數（鎖定時）
    """
    limiter = LoginLimiter(redis_conn)

    # 檢查是否被鎖定
    limit_status = await limiter.check_status(request.email)
    if limit_status.is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登入嘗試次數過多，帳號已暫時鎖定",
            headers={
                "X-RateLimit-Remaining": "0",
                "X-Lockout-Seconds": str(limit_status.lockout_seconds)
            }
        )

    # 查找用戶
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # 驗證用戶存在且密碼正確
    if not user or not verify_password(request.password, user.password_hash):
        # 記錄失敗並獲取更新狀態
        attempt_result = await limiter.record_failure(request.email)

        if attempt_result.is_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="登入嘗試次數過多，帳號已暫時鎖定",
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-Lockout-Seconds": str(attempt_result.lockout_seconds)
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email 或密碼錯誤",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-RateLimit-Remaining": str(attempt_result.remaining_attempts),
                    "X-Lockout-Seconds": "0"
                }
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

    # 登入成功，清除失敗記錄
    await limiter.clear_attempts(request.email)

    # 生成 JWT Token（包含 email 和 is_admin 資訊供前端使用）
    access_token, refresh_token = _generate_auth_tokens(
        str(user.id),
        email=user.email,
        email_verified=user.email_verified,
        is_admin=True
    )

    # 生成 CSRF Token 並設置 Cookie（HttpOnly Cookie 模式）
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, access_token, refresh_token, csrf_token)

    # 同時返回 Token（向後兼容 Bearer Token 模式）
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    response: Response,
    request: Optional[RefreshTokenRequest] = None,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db)
):
    """
    刷新 Access Token（支援 HttpOnly Cookie + Bearer Token 雙模式）

    - 優先從 Cookie 讀取 Refresh Token
    - 回退到請求體中的 Refresh Token
    - 驗證並返回新的 Token
    - 設置新的 HttpOnly Cookie
    """
    # 獲取 Refresh Token（優先 Cookie，回退 Request Body）
    token = refresh_token_cookie or (request.refresh_token if request else None)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供 Refresh Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 檢查 Token 是否在黑名單中
    if await token_blacklist.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 已失效，請重新登入",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 解碼 Refresh Token
    payload = decode_token(token)

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

    # 將舊的 Refresh Token 加入黑名單（Token 輪換，增強安全性）
    if payload.get("exp"):
        old_expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    else:
        old_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    await token_blacklist.add(token, old_expires_at)

    # 生成新的 Token（包含 email 和 is_admin 資訊供前端使用）
    new_access_token, new_refresh_token = _generate_auth_tokens(
        str(user.id),
        email=user.email,
        email_verified=user.email_verified,
        is_admin=user.is_admin if user.is_admin else None
    )

    # 生成 CSRF Token 並設置新 Cookie
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, new_access_token, new_refresh_token, csrf_token)

    # 同時返回 Token（向後兼容 Bearer Token 模式）
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=dict)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
):
    """
    用戶登出（支援 HttpOnly Cookie + Bearer Token 雙模式）

    - 將 Access Token 和 Refresh Token 加入黑名單
    - Token 在過期前都無法再使用
    - 清除所有認證 Cookie
    - 同時使 WebSocket 連接失效
    """
    tokens_blacklisted = []

    # 1. 黑名單化 Access Token（優先 Cookie，回退 Bearer）
    access_token = access_token_cookie or (credentials.credentials if credentials else None)
    if access_token:
        payload = decode_token(access_token)
        if payload and payload.get("exp"):
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        await token_blacklist.add(access_token, expires_at)
        tokens_blacklisted.append("access_token")

    # 2. 黑名單化 Refresh Token（從 Cookie 獲取）
    if refresh_token_cookie:
        payload = decode_token(refresh_token_cookie)
        if payload and payload.get("exp"):
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        await token_blacklist.add(refresh_token_cookie, expires_at)
        tokens_blacklisted.append("refresh_token")

    # 3. 清除所有認證 Cookie
    clear_auth_cookies(response)

    logger.info(f"User {current_user.id} logged out, tokens blacklisted: {tokens_blacklisted}")

    return {
        "message": "登出成功",
        "user_id": str(current_user.id),
        "tokens_invalidated": tokens_blacklisted
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

    # 信任分數加分：Email 驗證完成 +5
    await TrustScoreService.adjust_score(db, user.id, "email_verified")
    logger.info(f"Trust score increased for user {user.id} (email_verified)")

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

    # 生成新的驗證碼並發送 Email
    verification_code = generate_verification_code()
    await verification_codes.set(email, verification_code)

    # 發送驗證郵件
    username = email.split('@')[0]
    email_sent = await EmailService.send_verification_email(
        to_email=email,
        username=username,
        verification_code=verification_code
    )

    if email_sent:
        logger.info(f"Verification email resent to {mask_email(email)}")
    else:
        logger.error(f"Failed to resend verification email to {mask_email(email)}")

    return {
        "message": "驗證碼已重新發送",
        "email": email
    }


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    忘記密碼 - 發送密碼重置郵件

    - 檢查速率限制（60 秒冷卻 + 每日 5 次限制）
    - 生成重置 Token（32 字符，30 分鐘有效）
    - 發送密碼重置郵件到 Mailpit

    安全設計：
    - 無論 Email 是否存在，都返回相同訊息（防止用戶枚舉）
    - 使用 secrets.token_urlsafe() 生成強 Token
    - Token 存儲在資料庫，支援多實例部署
    """
    # 檢查速率限制
    await check_email_rate_limit(request.email)

    # 查找用戶
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    # 即使用戶不存在也返回成功（安全考量，不洩漏用戶是否存在）
    if not user:
        logger.info(f"Password reset requested for non-existent email: {mask_email(request.email)}")
        return {"message": "如果該信箱已註冊，我們已發送密碼重置郵件"}

    # 檢查帳號狀態
    if not user.is_active:
        logger.warning(f"Password reset requested for inactive user: {mask_email(request.email)}")
        return {"message": "如果該信箱已註冊，我們已發送密碼重置郵件"}

    # 生成重置 Token
    reset_token = secrets.token_urlsafe(32)
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    await db.commit()

    # 發送郵件
    username = request.email.split('@')[0]  # 使用 Email 前綴作為暫時用戶名
    email_sent = await EmailService.send_password_reset_email(
        to_email=request.email,
        username=username,
        reset_token=reset_token
    )

    if email_sent:
        logger.info(f"Password reset email sent to {mask_email(request.email)}")
    else:
        logger.error(f"Failed to send password reset email to {mask_email(request.email)}")

    return {"message": "如果該信箱已註冊，我們已發送密碼重置郵件"}


@router.get("/verify-reset-token", response_model=VerifyResetTokenResponse)
async def verify_reset_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    驗證密碼重置 Token 是否有效

    用於前端在顯示重置密碼表單前，先驗證 Token 是否有效。

    Returns:
        - valid=True: Token 有效，返回關聯的 Email
        - valid=False: Token 無效或已過期
    """
    # 查找擁有此 Token 的用戶
    result = await db.execute(
        select(User).where(User.password_reset_token == token)
    )
    user = result.scalar_one_or_none()

    if not user:
        return VerifyResetTokenResponse(valid=False, email=None)

    # 檢查 Token 是否過期
    if user.password_reset_expires < datetime.now(timezone.utc):
        # 清除過期的 Token
        user.password_reset_token = None
        user.password_reset_expires = None
        await db.commit()

        return VerifyResetTokenResponse(valid=False, email=None)

    return VerifyResetTokenResponse(valid=True, email=user.email)


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    重置密碼 - 使用重置 Token 設定新密碼

    安全設計：
    - Token 一次性使用，使用後立即清除
    - 驗證 Token 有效期
    - 使用 bcrypt 加密新密碼
    """
    # 查找擁有此 Token 的用戶
    result = await db.execute(
        select(User).where(User.password_reset_token == request.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的重置鏈接"
        )

    # 檢查 Token 是否過期
    if user.password_reset_expires < datetime.now(timezone.utc):
        # 清除過期的 Token
        user.password_reset_token = None
        user.password_reset_expires = None
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置鏈接已過期，請重新申請"
        )

    # 更新密碼
    user.password_hash = get_password_hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None

    await db.commit()

    logger.info(f"Password reset successful for user: {mask_email(user.email)}")

    return {"message": "密碼重置成功，請使用新密碼登入"}


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改密碼

    已登入用戶修改自己的密碼：
    - 驗證當前密碼
    - 檢查新密碼不能與舊密碼相同
    - 更新密碼
    - 使當前 Token 失效（強制重新登入）
    - 發送密碼變更通知 Email
    """
    # 1. 驗證當前密碼
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="當前密碼錯誤"
        )

    # 2. 檢查新密碼不能與舊密碼相同
    if verify_password(request.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密碼不能與當前密碼相同"
        )

    # 3. 更新密碼
    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    # 4. 將當前 Token 加入黑名單（使其失效）
    token = credentials.credentials
    payload = decode_token(token)
    if payload and payload.get("exp"):
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    await token_blacklist.add(token, expires_at)

    # 5. 發送密碼變更通知 Email
    username = current_user.email.split('@')[0]
    email_sent = await EmailService.send_password_changed_email(
        to_email=current_user.email,
        username=username
    )

    if email_sent:
        logger.info(f"Password changed notification sent to {mask_email(current_user.email)}")
    else:
        logger.warning(f"Failed to send password changed notification to {mask_email(current_user.email)}")

    logger.info(f"Password changed for user: {mask_email(current_user.email)}")

    return ChangePasswordResponse(
        message="密碼修改成功，請重新登入",
        tokens_invalidated=True
    )
