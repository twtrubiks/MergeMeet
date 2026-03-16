"""初始化興趣標籤數據"""

import asyncio
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.profile import InterestTag

# 預設興趣標籤
DEFAULT_INTEREST_TAGS = [
    # 運動 Sports
    {"name": "籃球", "category": "sports", "icon": "🏀"},
    {"name": "足球", "category": "sports", "icon": "⚽"},
    {"name": "羽毛球", "category": "sports", "icon": "🏸"},
    {"name": "健身", "category": "sports", "icon": "💪"},
    {"name": "瑜伽", "category": "sports", "icon": "🧘"},
    {"name": "游泳", "category": "sports", "icon": "🏊"},
    {"name": "登山", "category": "sports", "icon": "⛰️"},
    # 音樂 Music
    {"name": "流行音樂", "category": "music", "icon": "🎵"},
    {"name": "搖滾樂", "category": "music", "icon": "🎸"},
    {"name": "爵士樂", "category": "music", "icon": "🎷"},
    {"name": "古典音樂", "category": "music", "icon": "🎻"},
    {"name": "唱歌", "category": "music", "icon": "🎤"},
    # 美食 Food
    {"name": "烹飪", "category": "food", "icon": "🍳"},
    {"name": "烘焙", "category": "food", "icon": "🍰"},
    {"name": "咖啡", "category": "food", "icon": "☕"},
    {"name": "品酒", "category": "food", "icon": "🍷"},
    {"name": "美食探索", "category": "food", "icon": "🍽️"},
    # 旅遊 Travel
    {"name": "旅行", "category": "travel", "icon": "✈️"},
    {"name": "露營", "category": "travel", "icon": "🏕️"},
    {"name": "攝影", "category": "travel", "icon": "📸"},
    {"name": "背包旅行", "category": "travel", "icon": "🎒"},
    # 藝術 Art
    {"name": "繪畫", "category": "art", "icon": "🎨"},
    {"name": "手作", "category": "art", "icon": "✂️"},
    {"name": "設計", "category": "art", "icon": "🖌️"},
    {"name": "書法", "category": "art", "icon": "✍️"},
    # 閱讀 Reading
    {"name": "閱讀", "category": "reading", "icon": "📚"},
    {"name": "小說", "category": "reading", "icon": "📖"},
    {"name": "漫畫", "category": "reading", "icon": "📕"},
    {"name": "詩歌", "category": "reading", "icon": "📜"},
    # 科技 Tech
    {"name": "程式設計", "category": "tech", "icon": "💻"},
    {"name": "遊戲", "category": "tech", "icon": "🎮"},
    {"name": "攝影後製", "category": "tech", "icon": "🖥️"},
    {"name": "3C產品", "category": "tech", "icon": "📱"},
    # 寵物 Pets
    {"name": "貓咪", "category": "pets", "icon": "🐱"},
    {"name": "狗狗", "category": "pets", "icon": "🐶"},
    {"name": "寵物", "category": "pets", "icon": "🐾"},
    # 電影與戲劇 Entertainment
    {"name": "看電影", "category": "entertainment", "icon": "🎬"},
    {"name": "追劇", "category": "entertainment", "icon": "📺"},
    {"name": "動漫", "category": "entertainment", "icon": "🎭"},
    {"name": "戲劇", "category": "entertainment", "icon": "🎪"},
    # 其他 Others
    {"name": "投資理財", "category": "others", "icon": "💰"},
    {"name": "志工服務", "category": "others", "icon": "🤝"},
    {"name": "冥想", "category": "others", "icon": "🧘‍♂️"},
    {"name": "占星", "category": "others", "icon": "⭐"},
]


async def init_tags():
    """初始化興趣標籤"""
    print("🚀 開始初始化興趣標籤...")

    # 建立引擎
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    # 建立 Session
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # 建立所有表格
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 檢查是否已有標籤
        result = await session.execute(select(InterestTag))
        existing_tags = result.scalars().all()

        if existing_tags:
            print(f"⚠️  已存在 {len(existing_tags)} 個興趣標籤，跳過初始化")
            return

        # 添加所有標籤
        for tag_data in DEFAULT_INTEREST_TAGS:
            tag = InterestTag(**tag_data)
            session.add(tag)

        await session.commit()
        print(f"✅ 成功添加 {len(DEFAULT_INTEREST_TAGS)} 個興趣標籤")

    # 清除 Redis 興趣標籤快取
    r = None
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        keys = [key async for key in r.scan_iter(match="cache:interest_tags*")]
        if keys:
            await r.delete(*keys)
        print("🗑️  已清除興趣標籤 Redis 快取")
    except (aioredis.RedisError, ConnectionError):
        print("⚠️  Redis 快取清除失敗（Redis 可能未啟動）")
    finally:
        if r:
            await r.aclose()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_tags())
