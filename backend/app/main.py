"""MergeMeet FastAPI 主應用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db, close_db
from app.websocket.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    print("🚀 MergeMeet 啟動中...")
    # await init_db()  # 暫時註解，等資料庫啟動後再開啟

    # 啟動 WebSocket 心跳和清理任務
    await manager.start_background_tasks()

    yield
    # 關閉時執行
    print("👋 MergeMeet 關閉中...")
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
    """健康檢查"""
    return {
        "status": "healthy",
        "service": "MergeMeet API",
        "version": settings.VERSION
    }


@app.get("/api/hello")
async def hello_world():
    """Hello World 測試端點"""
    return {
        "message": "Hello from MergeMeet! 🎉",
        "status": "success"
    }


# ==================== API 路由 ====================
from app.api import auth, profile, discovery, safety, websocket, messages, admin, moderation

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["認證"])
app.include_router(profile.router, tags=["個人檔案"])
app.include_router(discovery.router, tags=["探索配對"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(messages.router, tags=["聊天訊息"])
app.include_router(safety.router, prefix=f"{settings.API_V1_PREFIX}/safety", tags=["安全功能"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["管理後台"])
app.include_router(moderation.router, prefix=f"{settings.API_V1_PREFIX}/moderation", tags=["內容審核"])

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
