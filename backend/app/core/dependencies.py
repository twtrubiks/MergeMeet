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


def _extract_token_from_cookie(
    access_token_cookie: Optional[str],
    csrf_token_header: Optional[str],
    csrf_token_cookie: Optional[str]
) -> str:
    """從 Cookie 提取並驗證 Token

    Args:
        access_token_cookie: Cookie 中的 Access Token
        csrf_token_header: Header 中的 CSRF Token
        csrf_token_cookie: Cookie 中的 CSRF Token

    Returns:
        str: 驗證後的 Token

    Raises:
        HTTPException: CSRF 驗證失敗
    """
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
    return access_token_cookie


def _validate_token_payload(payload: Optional[dict]) -> str:
    """驗證 Token payload 並返回 user_id

    Args:
        payload: 解碼後的 Token payload

    Returns:
        str: 用戶 ID

    Raises:
        HTTPException: Token 無效
    """
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Token 類型",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


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
    # 優先使用 Cookie 認證，回退到 Bearer Token
    if access_token_cookie:
        token = _extract_token_from_cookie(
            access_token_cookie, csrf_token_header, csrf_token_cookie
        )
    elif credentials:
        token = credentials.credentials
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

    # 解碼並驗證 Token
    payload = decode_token(token)
    user_id = _validate_token_payload(payload)

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
