"""測試配置與 Fixtures"""
import pytest
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.main import app
from app.core.database import Base, get_db

# 測試資料庫 URL（使用獨立的 PostgreSQL 測試資料庫）
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
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """測試資料庫 Session"""
    # 建立測試引擎
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # 測試環境不使用連接池
    )

    # 建立所有表格（包含 PostGIS 擴展）
    async with engine.begin() as conn:
        # 確保 PostGIS 擴展已啟用
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)

    # 建立 Session
    TestSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    # 清理（刪除所有表格）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


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
