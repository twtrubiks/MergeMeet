"""
Cookie 工具函數

提供 HttpOnly Cookie 設置與清除功能，用於安全的 Token 存儲。

安全特性：
- HttpOnly: 防止 JavaScript 存取（XSS 防護）
- Secure: 僅 HTTPS 傳輸（生產環境）
- SameSite: 防止 CSRF（Strict 或 Lax）
"""
import secrets
from typing import Optional
from fastapi import Response

from app.core.config import settings


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str
) -> None:
    """設置認證 Cookie

    Args:
        response: FastAPI Response 物件
        access_token: JWT Access Token
        refresh_token: JWT Refresh Token
        csrf_token: CSRF Token（用於 Double Submit Cookie Pattern）
    """
    # 處理 domain 設置（空字串時不設置 domain）
    domain = settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None

    # Access Token Cookie (HttpOnly)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=settings.COOKIE_PATH,
        domain=domain
    )

    # Refresh Token Cookie (HttpOnly，限制路徑)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/auth",  # 限制只在 auth 路由可用
        domain=domain
    )

    # CSRF Token Cookie (可被 JS 讀取，用於 Double Submit)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # 必須為 False，前端 JS 需要讀取
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=settings.COOKIE_PATH,
        domain=domain
    )


def clear_auth_cookies(response: Response) -> None:
    """清除所有認證 Cookie

    Args:
        response: FastAPI Response 物件
    """
    domain = settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None

    # 清除 Access Token
    response.delete_cookie(
        key="access_token",
        path=settings.COOKIE_PATH,
        domain=domain
    )

    # 清除 Refresh Token
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        domain=domain
    )

    # 清除 CSRF Token
    response.delete_cookie(
        key="csrf_token",
        path=settings.COOKIE_PATH,
        domain=domain
    )


def generate_csrf_token() -> str:
    """生成 CSRF Token

    使用 secrets 模組生成密碼學安全的隨機字串

    Returns:
        str: URL 安全的隨機 CSRF Token
    """
    return secrets.token_urlsafe(settings.CSRF_TOKEN_LENGTH)


def get_cookie_value(cookie_string: Optional[str], cookie_name: str) -> Optional[str]:
    """從 Cookie 字串中提取特定 Cookie 值

    Args:
        cookie_string: 完整的 Cookie 字串
        cookie_name: 要提取的 Cookie 名稱

    Returns:
        Optional[str]: Cookie 值，不存在則返回 None
    """
    if not cookie_string:
        return None

    cookies = cookie_string.split("; ")
    for cookie in cookies:
        if cookie.startswith(f"{cookie_name}="):
            return cookie[len(cookie_name) + 1:]
    return None
