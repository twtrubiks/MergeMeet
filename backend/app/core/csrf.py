"""
CSRF 防護模組

使用 Double Submit Cookie Pattern：
1. 登入時，後端生成 CSRF Token 設置為非 HttpOnly Cookie
2. 前端從 Cookie 讀取 CSRF Token，放入請求 Header (X-CSRF-Token)
3. 後端比較 Cookie 和 Header 中的 Token 是否一致

原理：
- 攻擊者可以讓用戶的瀏覽器發送 Cookie，但無法讀取 Cookie 內容
- 因此攻擊者無法構造正確的 X-CSRF-Token Header
- 結合 SameSite Cookie 提供額外保護
"""
from typing import Optional
from fastapi import HTTPException, status, Request, Cookie, Header


async def verify_csrf_token(
    request: Request,
    csrf_token_header: Optional[str] = Header(None, alias="X-CSRF-Token"),
    csrf_token_cookie: Optional[str] = Cookie(None, alias="csrf_token"),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
) -> bool:
    """驗證 CSRF Token

    Double Submit Cookie Pattern 驗證邏輯：
    - 只有使用 Cookie 認證時才需要 CSRF 驗證
    - Bearer Token 認證不需要 CSRF（Token 本身就是防護）
    - GET/HEAD/OPTIONS 等安全方法豁免驗證

    Args:
        request: FastAPI Request 物件
        csrf_token_header: 從 Header 獲取的 CSRF Token
        csrf_token_cookie: 從 Cookie 獲取的 CSRF Token
        access_token_cookie: 從 Cookie 獲取的 Access Token

    Returns:
        bool: 驗證成功返回 True

    Raises:
        HTTPException: CSRF 驗證失敗時拋出 403 錯誤
    """
    # 安全方法豁免（GET, HEAD, OPTIONS 不修改資料）
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True

    # 檢查是否使用 Cookie 認證
    if not access_token_cookie:
        # 使用 Bearer Token 認證，不需要 CSRF 驗證
        # Bearer Token 本身就是防護（攻擊者無法獲得 Token）
        return True

    # Cookie 認證需要驗證 CSRF Token
    if not csrf_token_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF 驗證失敗：缺少 X-CSRF-Token Header"
        )

    if not csrf_token_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF 驗證失敗：缺少 csrf_token Cookie"
        )

    if csrf_token_header != csrf_token_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF 驗證失敗：Token 不匹配"
        )

    return True


def is_csrf_exempt(request: Request) -> bool:
    """檢查請求是否豁免 CSRF 驗證

    以下情況豁免：
    1. 安全方法（GET, HEAD, OPTIONS）
    2. 沒有使用 Cookie 認證（使用 Bearer Token）

    Args:
        request: FastAPI Request 物件

    Returns:
        bool: 是否豁免 CSRF 驗證
    """
    # 安全方法豁免
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True

    # 檢查是否使用 Cookie 認證
    access_token_cookie = request.cookies.get("access_token")
    if not access_token_cookie:
        return True

    return False
