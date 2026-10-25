"""認證依賴（get_current_user 等）單元測試

逐一檢查每個拒絕分支的狀態碼、訊息與 WWW-Authenticate header；
Cookie／Bearer 的 API 整合流程見 test_cookie_auth.py。
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dependencies
from app.core.config import settings
from app.core.dependencies import (
    get_current_active_user,
    get_current_admin_user,
    get_current_user,
)
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User

BEARER = {"WWW-Authenticate": "Bearer"}


@pytest.fixture
def blacklist(monkeypatch):
    mock = AsyncMock(return_value=False)
    monkeypatch.setattr(dependencies.token_blacklist, "is_blacklisted", mock)
    return mock


@pytest.fixture
def invalidator(monkeypatch):
    mock = AsyncMock(return_value=True)
    monkeypatch.setattr(dependencies.TokenInvalidator, "is_token_valid", mock)
    return mock


@pytest.fixture
async def user(test_db: AsyncSession) -> User:
    user = User(email="deps@example.com", password_hash="x", date_of_birth=date(1995, 1, 1))
    test_db.add(user)
    await test_db.commit()
    return user


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def authenticate(db: AsyncSession, *, credentials=None, cookie=None, header=None, csrf=None):
    return await get_current_user(
        credentials=credentials,
        access_token_cookie=cookie,
        csrf_token_header=header,
        csrf_token_cookie=csrf,
        db=db,
    )


async def rejection(db: AsyncSession, **kwargs) -> tuple[int, str, dict | None]:
    with pytest.raises(HTTPException) as exc_info:
        await authenticate(db, **kwargs)
    exc = exc_info.value
    return exc.status_code, exc.detail, exc.headers


@pytest.mark.usefixtures("blacklist", "invalidator")
class TestGetCurrentUser:
    async def test_bearer_token(self, test_db: AsyncSession, user: User, invalidator):
        token = create_access_token({"sub": str(user.id)})

        assert (await authenticate(test_db, credentials=bearer(token))).id == user.id
        [call] = invalidator.await_args_list
        assert call.args[0] == str(user.id)
        assert isinstance(call.args[1], int) and call.args[1] > 0  # iat

    async def test_cookie_preferred_over_bearer(self, test_db: AsyncSession, user: User):
        """同時帶 Cookie 與 Bearer 時以 Cookie 為準（並因此必須通過 CSRF 驗證）"""
        other = User(email="other@example.com", password_hash="x", date_of_birth=date(1995, 1, 1))
        test_db.add(other)
        await test_db.commit()

        result = await authenticate(
            test_db,
            credentials=bearer(create_access_token({"sub": str(other.id)})),
            cookie=create_access_token({"sub": str(user.id)}),
            header="csrf",
            csrf="csrf",
        )

        assert result.id == user.id

    async def test_no_credentials(self, test_db: AsyncSession):
        assert await rejection(test_db) == (401, "未提供認證憑證", BEARER)

    @pytest.mark.parametrize(
        ("header", "csrf", "detail"),
        [
            (None, "csrf", "CSRF 驗證失敗：缺少 CSRF Token"),
            ("csrf", None, "CSRF 驗證失敗：缺少 CSRF Token"),
            ("csrf", "other", "CSRF 驗證失敗：Token 不匹配"),
        ],
        ids=["no-header", "no-cookie", "mismatch"],
    )
    async def test_cookie_requires_matching_csrf(
        self, test_db: AsyncSession, user: User, header, csrf, detail
    ):
        token = create_access_token({"sub": str(user.id)})

        assert await rejection(
            test_db, credentials=bearer(token), cookie=token, header=header, csrf=csrf
        ) == (403, detail, None)

    async def test_blacklisted_token(self, test_db: AsyncSession, user: User, blacklist):
        token = create_access_token({"sub": str(user.id)})
        blacklist.return_value = True

        assert await rejection(test_db, credentials=bearer(token)) == (
            401,
            "Token 已失效，請重新登入",
            BEARER,
        )
        blacklist.assert_awaited_once_with(token)

    async def test_malformed_token(self, test_db: AsyncSession):
        assert await rejection(test_db, credentials=bearer("not-a-jwt")) == (
            401,
            "無效的認證憑證",
            BEARER,
        )

    async def test_refresh_token_rejected(self, test_db: AsyncSession, user: User):
        token = create_refresh_token({"sub": str(user.id)})

        assert await rejection(test_db, credentials=bearer(token)) == (
            401,
            "無效的 Token 類型",
            BEARER,
        )

    async def test_token_without_subject(self, test_db: AsyncSession):
        token = create_access_token({"email": "deps@example.com"})

        assert await rejection(test_db, credentials=bearer(token)) == (
            401,
            "無效的 Token",
            BEARER,
        )

    async def test_globally_invalidated_token(self, test_db: AsyncSession, user: User, invalidator):
        invalidator.return_value = False
        token = create_access_token({"sub": str(user.id)})

        assert await rejection(test_db, credentials=bearer(token)) == (
            401,
            "Token 已失效（密碼已變更），請重新登入",
            BEARER,
        )

    async def test_token_without_iat_checked_as_issued_at_epoch(
        self, test_db: AsyncSession, user: User, invalidator
    ):
        """缺少 iat 視為最早簽發：只要有全局失效記錄就無效"""
        token = jwt.encode(
            {
                "sub": str(user.id),
                "type": "access",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        await authenticate(test_db, credentials=bearer(token))

        invalidator.assert_awaited_once_with(str(user.id), 0)

    async def test_unknown_user(self, test_db: AsyncSession):
        token = create_access_token({"sub": str(uuid.uuid4())})

        assert await rejection(test_db, credentials=bearer(token)) == (
            401,
            "用戶不存在",
            BEARER,
        )

    async def test_inactive_user(self, test_db: AsyncSession, user: User):
        user.is_active = False
        await test_db.commit()
        token = create_access_token({"sub": str(user.id)})

        assert await rejection(test_db, credentials=bearer(token)) == (403, "帳號已被停用", None)


class TestRoleDependencies:
    async def test_active_user_passthrough(self, user: User):
        assert await get_current_active_user(user) is user

    async def test_admin_required(self, user: User):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(user)

        assert (exc_info.value.status_code, exc_info.value.detail) == (403, "需要管理員權限")

    async def test_admin_allowed(self, user: User):
        user.is_admin = True

        assert await get_current_admin_user(user) is user
