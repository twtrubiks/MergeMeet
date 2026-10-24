"""安全工具測試（JWT 過期時間）"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import security
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token

FROZEN_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    """凍結 security 內的 datetime.now，並模擬部署在台灣時區（UTC+8）的主機

    PyJWT 把 naive datetime 當作 UTC；若誤用不帶時區的 now()，
    在 UTC+8 主機上 Token 會多活 8 小時（在 UTC 主機上無從察覺）。
    """

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return (FROZEN_NOW + timedelta(hours=8)).replace(tzinfo=None)
            return FROZEN_NOW.astimezone(tz)

    monkeypatch.setattr(security, "datetime", _FrozenDatetime)


@pytest.mark.parametrize(
    ("create_token", "token_type", "lifetime"),
    [
        (create_access_token, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
        (create_refresh_token, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)),
    ],
)
def test_token_expiry_counted_from_utc_now(create_token, token_type, lifetime):
    """測試：Token 的 exp / iat 以 UTC 現在時間計算"""
    claims = jwt.decode(
        create_token({"sub": "user-1"}),
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_exp": False},
    )

    assert claims["type"] == token_type
    assert claims["exp"] == int((FROZEN_NOW + lifetime).timestamp())
    assert claims["iat"] == int(FROZEN_NOW.timestamp())
