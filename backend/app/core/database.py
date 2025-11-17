"""資料庫連接配置"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

from app.core.config import settings

# 建立非同步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # 開發環境顯示 SQL
    future=True,
    pool_size=5,  # 減少基礎連接數（適合小型應用）
    max_overflow=10,  # 減少最大溢出連接數
    pool_recycle=3600,  # 1 小時回收連接
    pool_pre_ping=True,  # 連接前先 ping，確保連接有效
)

# 建立 Session 工廠
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 建立 Base 類別
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """取得資料庫 Session（依賴注入）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化資料庫（建立所有表格）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """關閉資料庫連接"""
    await engine.dispose()
