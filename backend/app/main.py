"""MergeMeet FastAPI 主應用

TODO: 全局速率限制（上線前建議完成）
- 目前無全局 API 速率限制，存在 DoS 攻擊風險
- 建議：整合 slowapi 或 fastapi-limiter
- 配置：每 IP 每分鐘最多 60 請求
- 特殊端點（登入、註冊）可設置更嚴格限制
- 參考：https://github.com/laurentS/slowapi
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import asyncio

from app.core.config import settings
from app.core.database import close_db
from app.websocket.manager import manager
from app.services.redis_client import redis_client, get_redis
from app.services.token_blacklist import token_blacklist
from app.services.content_moderation import ContentModerationService
from app.api.auth import verification_codes
from app.api import auth, profile, discovery, safety, websocket, messages, admin, moderation, notifications

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    logger.info("🚀 MergeMeet 啟動中...")
    # await init_db()  # 暫時註解，等資料庫啟動後再開啟

    # 初始化 Redis 連線給各服務
    try:
        redis_conn = await get_redis()
        logger.info("✅ Redis 連線成功")

        # 設置 Token 黑名單 Redis 連線
        await token_blacklist.set_redis(redis_conn)

        # 設置驗證碼存儲 Redis 連線
        await verification_codes.set_redis(redis_conn)

        # 設置內容審核服務 Redis 連線
        await ContentModerationService.set_redis(redis_conn)

        logger.info("✅ Redis 已整合至 Token 黑名單、驗證碼存儲、內容審核快取")
    except Exception as e:
        logger.warning(f"⚠️ Redis 連線失敗，服務將使用內存回退模式: {e}")

    # 啟動 Token 黑名單定期清理任務（用於內存回退時）
    await token_blacklist.start_cleanup_task()

    # 啟動 WebSocket 心跳和清理任務
    await manager.start_background_tasks()

    yield
    # 關閉時執行
    logger.info("👋 MergeMeet 關閉中...")

    # 停止 Token 黑名單清理任務
    await token_blacklist.stop_cleanup_task()

    await redis_client.close()
    await close_db()


# 建立 FastAPI 應用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MergeMeet 交友平台 API",
    lifespan=lifespan,
    redirect_slashes=False,  # 禁用自動重定向，統一不使用 trailing slash
)

# CORS 中間件（安全配置）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,  # 僅允許指定來源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # 明確指定允許的 HTTP 方法
    allow_headers=["Authorization", "Content-Type", "Accept"],  # 僅允許必要的 headers
)

# 靜態檔案（照片上傳）
uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


# ==================== 路由 ====================

@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "歡迎使用 MergeMeet API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康檢查（包含 Redis 狀態）

    Returns:
        健康狀態資訊，包含服務版本和 Redis 連接狀態
    """
    health_status = {
        "status": "healthy",
        "service": "MergeMeet API",
        "version": settings.VERSION,
        "redis": {
            "token_blacklist": token_blacklist.is_using_redis(),
            "verification_codes": verification_codes.is_using_redis(),
            "content_moderation": ContentModerationService.is_using_redis()
        }
    }

    # 嘗試 ping Redis（帶超時保護）
    try:
        redis_conn = await get_redis()
        # 使用 asyncio.wait_for 添加 1 秒超時
        await asyncio.wait_for(redis_conn.ping(), timeout=1.0)
        health_status["redis"]["connected"] = True
    except asyncio.TimeoutError:
        health_status["redis"]["connected"] = False
        health_status["redis"]["error"] = "Timeout"
        logger.warning("Redis health check timeout")
    except Exception as e:
        health_status["redis"]["connected"] = False
        health_status["redis"]["error"] = str(e)
        logger.warning(f"Redis health check failed: {e}")

    return health_status


@app.get("/api/hello")
async def hello_world():
    """Hello World 測試端點"""
    return {
        "message": "Hello from MergeMeet! 🎉",
        "status": "success"
    }


# ==================== API 路由 ====================

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["認證"])
app.include_router(profile.router, tags=["個人檔案"])
app.include_router(discovery.router, tags=["探索配對"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(messages.router, tags=["聊天訊息"])
app.include_router(safety.router, prefix=f"{settings.API_V1_PREFIX}/safety", tags=["安全功能"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["管理後台"])
app.include_router(moderation.router, prefix=f"{settings.API_V1_PREFIX}/moderation", tags=["內容審核"])
app.include_router(notifications.router, tags=["通知"])

# 未來將加入的路由
# app.include_router(matches.router, prefix=f"{settings.API_V1_PREFIX}/matches", tags=["配對管理"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
