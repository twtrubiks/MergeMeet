"""安全工具測試（密碼雜湊與驗證、JWT 過期時間）"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import security
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)

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


def test_access_token_custom_lifetime():
    """測試：指定 expires_delta 時以它計算過期時間（同樣以 UTC 為準）"""
    claims = jwt.decode(
        create_access_token({"sub": "user-1"}, expires_delta=timedelta(minutes=5)),
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_exp": False},
    )

    assert claims["exp"] == int((FROZEN_NOW + timedelta(minutes=5)).timestamp())


class TestPassword:
    """密碼雜湊與驗證"""

    def test_verify_correct_and_wrong_password(self):
        hashed = get_password_hash("Correct123")

        assert verify_password("Correct123", hashed) is True
        assert verify_password("Wrong12345", hashed) is False

    def test_malformed_stored_hash_rejects_any_password(self):
        """資料庫中的雜湊格式錯誤時一律驗證失敗：不可拋錯，更不可放行"""
        assert verify_password("anything", "not-a-bcrypt-hash") is False

    def test_passwords_differ_only_beyond_bcrypt_72_bytes(self):
        """SHA256 預處理：bcrypt 只看前 72 bytes，後段不同的長密碼仍須能區分"""
        prefix = "a" * 80
        hashed = get_password_hash(prefix + "1")

        assert verify_password(prefix + "2", hashed) is False

    def test_password_length_limit(self):
        """128 字元以內可用；超過時拒絕雜湊，驗證則視為失敗（登入回 401 而非 500）"""
        hashed = get_password_hash("a" * 128)

        assert verify_password("a" * 128, hashed) is True
        assert verify_password("a" * 129, hashed) is False
        with pytest.raises(ValueError, match="128"):
            get_password_hash("a" * 129)
