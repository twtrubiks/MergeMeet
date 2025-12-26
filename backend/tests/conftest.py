"""測試配置與 Fixtures"""
import pytest
import pytest_asyncio
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from dotenv import load_dotenv

# 載入 .env 檔案（讓 os.getenv 可以讀取）
load_dotenv()

from app.main import app
from app.core.database import Base, get_db
from app.services.content_moderation import ContentModerationService
from app.services.photo_moderation import PhotoModerationService

# 測試資料庫 URL（使用獨立的 PostgreSQL 測試資料庫）
# 優先從環境變數讀取，預設值僅作為提醒
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://mergemeet:YOUR_DB_PASSWORD_HERE@localhost:5432/mergemeet_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """建立事件循環"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """測試資料庫 Session（主要使用名稱）"""
    # 建立測試引擎
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    ContentModerationService.set_session_factory(TestSessionLocal)
    PhotoModerationService.set_session_factory(TestSessionLocal)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    ContentModerationService.reset_session_factory()
    PhotoModerationService.reset_session_factory()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """測試資料庫 Session（別名，向後兼容）"""
    yield db_session


@pytest.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """測試 HTTP Client"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_data():
    """範例用戶資料"""
    return {
        "email": "test@example.com",
        "password": "Test1234!",
        "date_of_birth": "1995-01-01"
    }


# ==================== Redis Mock Fixtures ====================

@pytest.fixture
def mock_redis():
    """建立 Mock Redis 連線

    模擬 Redis 的基本操作：setex, get, exists, delete, ttl
    """
    redis = AsyncMock()
    # 內部存儲（模擬 Redis 行為）
    _storage = {}

    async def mock_setex(key: str, ttl: int, value: str):
        _storage[key] = value
        return True

    async def mock_get(key: str):
        return _storage.get(key)

    async def mock_exists(key: str):
        return 1 if key in _storage else 0

    async def mock_delete(key: str):
        if key in _storage:
            del _storage[key]
            return 1
        return 0

    async def mock_ttl(key: str):
        return 300 if key in _storage else -2

    redis.setex = AsyncMock(side_effect=mock_setex)
    redis.get = AsyncMock(side_effect=mock_get)
    redis.exists = AsyncMock(side_effect=mock_exists)
    redis.delete = AsyncMock(side_effect=mock_delete)
    redis.ttl = AsyncMock(side_effect=mock_ttl)
    redis._storage = _storage  # 暴露存儲供測試使用

    return redis


@pytest.fixture
def mock_redis_error():
    """建立會拋出 RedisError 的 Mock Redis

    用於測試 Redis 不可用時的回退行為
    """
    import redis.asyncio as aioredis

    redis = AsyncMock()
    redis.setex = AsyncMock(side_effect=aioredis.RedisError("Connection refused"))
    redis.get = AsyncMock(side_effect=aioredis.RedisError("Connection refused"))
    redis.exists = AsyncMock(side_effect=aioredis.RedisError("Connection refused"))
    redis.delete = AsyncMock(side_effect=aioredis.RedisError("Connection refused"))

    return redis


# ==================== 認證 Fixtures ====================


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, sample_user_data: dict) -> str:
    """取得認證 Token（純 Bearer Token 模式）

    自動處理 Cookie 清除，確保測試使用 Bearer Token 認證。
    用於測試業務邏輯，不測試認證機制本身。

    Note:
        Cookie + CSRF 認證的測試請參考 test_cookie_auth.py
    """
    response = await client.post("/api/auth/register", json=sample_user_data)
    assert response.status_code == 201
    token = response.json()["access_token"]
    client.cookies.clear()
    return token


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    """認證 Headers（便捷用法）

    Example:
        async def test_get_profile(client, auth_headers):
            response = await client.get("/api/profile", headers=auth_headers)
            assert response.status_code == 200
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def auth_user(client: AsyncClient, sample_user_data: dict) -> dict:
    """取得認證用戶完整資訊

    Returns:
        dict: {"token": str, "email": str, "headers": dict}
    """
    response = await client.post("/api/auth/register", json=sample_user_data)
    assert response.status_code == 201
    token = response.json()["access_token"]
    client.cookies.clear()
    return {
        "token": token,
        "email": sample_user_data["email"],
        "headers": {"Authorization": f"Bearer {token}"}
    }


@pytest_asyncio.fixture
async def auth_user_pair(client: AsyncClient) -> dict:
    """建立兩個已認證用戶（Alice & Bob）

    Returns:
        dict: {"alice": {...}, "bob": {...}}
    """
    alice_data = {
        "email": "alice@example.com",
        "password": "Alice1234!",
        "date_of_birth": "1995-01-01"
    }
    bob_data = {
        "email": "bob@example.com",
        "password": "Bob12345!",
        "date_of_birth": "1996-06-15"
    }

    # 註冊 Alice
    resp_a = await client.post("/api/auth/register", json=alice_data)
    assert resp_a.status_code == 201
    token_a = resp_a.json()["access_token"]
    client.cookies.clear()

    # 註冊 Bob
    resp_b = await client.post("/api/auth/register", json=bob_data)
    assert resp_b.status_code == 201
    token_b = resp_b.json()["access_token"]
    client.cookies.clear()

    return {
        "alice": {
            "token": token_a,
            "email": alice_data["email"],
            "headers": {"Authorization": f"Bearer {token_a}"}
        },
        "bob": {
            "token": token_b,
            "email": bob_data["email"],
            "headers": {"Authorization": f"Bearer {token_b}"}
        }
    }


@pytest_asyncio.fixture
async def auth_user_trio(client: AsyncClient) -> dict:
    """建立三個已認證用戶（Alice, Bob, Charlie）

    用於需要三方互動的測試場景（如封鎖功能）

    Returns:
        dict: {"alice": {...}, "bob": {...}, "charlie": {...}}
    """
    users_data = [
        {"email": "alice@example.com", "password": "Alice1234!", "date_of_birth": "1995-01-01"},
        {"email": "bob@example.com", "password": "Bob12345!", "date_of_birth": "1996-06-15"},
        {"email": "charlie@example.com", "password": "Charlie1!", "date_of_birth": "1994-03-20"},
    ]

    result = {}
    for user_data, name in zip(users_data, ["alice", "bob", "charlie"]):
        resp = await client.post("/api/auth/register", json=user_data)
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        client.cookies.clear()
        result[name] = {
            "token": token,
            "email": user_data["email"],
            "headers": {"Authorization": f"Bearer {token}"}
        }

    return result
