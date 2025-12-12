"""安全相關工具：JWT 認證、密碼加密"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 密碼加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _pre_hash_password(password: str) -> str:
    """
    對密碼進行預處理（SHA256），避免 bcrypt 的 72 bytes 限制

    Args:
        password: 原始密碼

    Returns:
        SHA256 哈希後的十六進制字串

    Raises:
        ValueError: 密碼長度超過限制
    """
    # 防止 DoS 攻擊：限制密碼最大長度
    MAX_PASSWORD_LENGTH = 128
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"密碼長度不能超過 {MAX_PASSWORD_LENGTH} 字元")

    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼

    Args:
        plain_password: 明文密碼
        hashed_password: bcrypt 加密後的密碼

    Returns:
        密碼是否正確
    """
    # 先對密碼進行 SHA256 預處理，再用 bcrypt 驗證
    pre_hashed = _pre_hash_password(plain_password)
    return pwd_context.verify(pre_hashed, hashed_password)


def get_password_hash(password: str) -> str:
    """
    將密碼加密

    Args:
        password: 明文密碼

    Returns:
        bcrypt 加密後的密碼
    """
    # 先對密碼進行 SHA256 預處理，避免 bcrypt 的 72 bytes 限制
    pre_hashed = _pre_hash_password(password)
    return pwd_context.hash(pre_hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    建立 JWT Access Token

    Args:
        data: 要編碼的資料（通常包含 sub: user_id）
        expires_delta: 過期時間（預設從設定檔讀取）

    Returns:
        JWT Token 字串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = (
            datetime.now(timezone.utc)
            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    建立 JWT Refresh Token

    Args:
        data: 要編碼的資料（通常包含 sub: user_id）

    Returns:
        JWT Refresh Token 字串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    解碼 JWT Token

    Args:
        token: JWT Token 字串

    Returns:
        解碼後的資料，若失敗則返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
