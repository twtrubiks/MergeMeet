"""認證 Cookie 屬性測試

Cookie 的屬性決定安全性：access/refresh token 必須 HttpOnly（防 XSS 讀取），
CSRF token 必須能被前端讀取；清除時 path／domain 必須與設置時相同，否則瀏覽器不會刪除。
"""

from http.cookies import SimpleCookie

import pytest
from starlette.responses import Response

from app.core.config import settings
from app.core.cookie_utils import clear_auth_cookies, generate_csrf_token, set_auth_cookies


def parse_set_cookies(response: Response) -> dict[str, dict]:
    """把每個 Set-Cookie header 解析成 {name: {"value": ..., 屬性: ...}}"""
    cookies = {}
    for header in response.headers.getlist("set-cookie"):
        parsed = SimpleCookie()
        parsed.load(header)
        [(name, morsel)] = parsed.items()
        cookies[name] = {
            "value": morsel.value,
            **{key: morsel[key] for key in morsel if morsel[key] != ""},
        }
    return cookies


@pytest.fixture
def cookie_settings(monkeypatch):
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "COOKIE_SAMESITE", "strict")
    monkeypatch.setattr(settings, "COOKIE_DOMAIN", "mergemeet.example")
    monkeypatch.setattr(settings, "COOKIE_PATH", "/")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    monkeypatch.setattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)


def test_set_auth_cookies_attributes(cookie_settings):
    response = Response()

    set_auth_cookies(response, "access-jwt", "refresh-jwt", "csrf-value")

    common = {"secure": True, "samesite": "strict", "domain": "mergemeet.example"}
    assert parse_set_cookies(response) == {
        "access_token": {
            "value": "access-jwt",
            "httponly": True,
            "max-age": "1800",
            "path": "/",
            **common,
        },
        # refresh token 只送往 /api/auth，其他 API 請求不會帶上
        "refresh_token": {
            "value": "refresh-jwt",
            "httponly": True,
            "max-age": str(7 * 24 * 60 * 60),
            "path": "/api/auth",
            **common,
        },
        # 前端 JS 要讀取後放進 X-CSRF-Token header，不可 HttpOnly
        "csrf_token": {"value": "csrf-value", "max-age": "1800", "path": "/", **common},
    }


def test_clear_auth_cookies_matches_set_path_and_domain(cookie_settings):
    response = Response()

    clear_auth_cookies(response)

    cookies = parse_set_cookies(response)
    assert set(cookies) == {"access_token", "refresh_token", "csrf_token"}
    assert {name: (c["path"], c["domain"], c["max-age"]) for name, c in cookies.items()} == {
        "access_token": ("/", "mergemeet.example", "0"),
        "refresh_token": ("/api/auth", "mergemeet.example", "0"),
        "csrf_token": ("/", "mergemeet.example", "0"),
    }


def test_empty_domain_omits_domain_attribute(monkeypatch):
    """COOKIE_DOMAIN 為空字串時不設 Domain（只屬於當前網域）"""
    monkeypatch.setattr(settings, "COOKIE_DOMAIN", "")
    set_response, clear_response = Response(), Response()

    set_auth_cookies(set_response, "a", "r", "c")
    clear_auth_cookies(clear_response)

    for response in (set_response, clear_response):
        assert all("domain" not in c for c in parse_set_cookies(response).values())


def test_generate_csrf_token_is_random_and_long_enough():
    tokens = {generate_csrf_token() for _ in range(5)}

    assert len(tokens) == 5
    # token_urlsafe(n) 產生 n bytes 亂數的 base64url 字串
    assert all(len(token) >= settings.CSRF_TOKEN_LENGTH * 4 // 3 for token in tokens)
