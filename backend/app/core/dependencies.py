"""依賴注入函數"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.token_blacklist import token_blacklist

# 可選的 Bearer Token（用於支援雙模式認證）
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    csrf_token_header: Optional[str] = Header(None, alias="X-CSRF-Token"),
    csrf_token_cookie: Optional[str] = Cookie(None, alias="csrf_token"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    取得當前登入用戶（支援雙模式認證）

    認證方式：
    1. Cookie + CSRF Token（優先）- Web 前端使用，防止 XSS
    2. Bearer Token（回退）- API 客戶端 / 移動端使用

    Args:
        credentials: Bearer Token 認證憑證（可選）
        access_token_cookie: Cookie 中的 Access Token（可選）
        csrf_token_header: Header 中的 CSRF Token
        csrf_token_cookie: Cookie 中的 CSRF Token
        db: 資料庫 Session

    Raises:
        HTTPException: 如果認證失敗
    """
    token = None
    auth_method = None

    # 優先使用 Cookie 認證
    if access_token_cookie:
        # Cookie 認證需要驗證 CSRF Token（Double Submit Cookie Pattern）
        if not csrf_token_header or not csrf_token_cookie:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF 驗證失敗：缺少 CSRF Token"
            )
        if csrf_token_header != csrf_token_cookie:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF 驗證失敗：Token 不匹配"
            )
        token = access_token_cookie
        auth_method = "cookie"
    elif credentials:
        # 回退到 Bearer Token 認證
        token = credentials.credentials
        auth_method = "bearer"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 檢查 Token 是否在黑名單中（已登出）
    if await token_blacklist.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已失效，請重新登入",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 解碼 Token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 檢查 Token 類型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Token 類型",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 取得用戶 ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 從資料庫查詢用戶
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 檢查用戶是否啟用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    取得當前啟用的用戶

    這是 get_current_user 的別名，用於明確表示需要啟用的用戶
    """
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    取得當前管理員用戶

    檢查用戶是否具有管理員權限

    Raises:
        HTTPException: 如果用戶不是管理員
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )

    return current_user
