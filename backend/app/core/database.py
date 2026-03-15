"""資料庫連接配置"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# 建立非同步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",  # 僅開發環境顯示 SQL，生產環境關閉以提升性能
    future=True,
    pool_size=settings.DB_POOL_SIZE,  # 從配置讀取連接池大小
    max_overflow=settings.DB_MAX_OVERFLOW,  # 從配置讀取最大溢出連接數
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
    """取得資料庫 Session（依賴注入）

    Transaction 由 handler 自行管理，需明確呼叫 await db.commit()。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """初始化資料庫（建立所有表格）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """關閉資料庫連接"""
    await engine.dispose()
