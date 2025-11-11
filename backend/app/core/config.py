"""應用程式配置"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """應用程式設定"""

    # 專案資訊
    PROJECT_NAME: str = "MergeMeet"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # 資料庫
    DATABASE_URL: str = "postgresql+asyncpg://mergemeet:YOUR_DB_PASSWORD_HERE@localhost:5432/mergemeet"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production-min-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    # 檔案上傳
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_DIR: str = "uploads"

    # Email（暫時使用控制台輸出）
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
