"""應用程式配置"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """應用程式設定"""

    # 專案資訊
    PROJECT_NAME: str = "MergeMeet"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # 資料庫（必須從環境變數設定）
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://mergemeet:YOUR_DB_PASSWORD_HERE@localhost:5432/mergemeet"
    )

    # Redis（目前未使用，保留供未來多伺服器部署時整合）
    # TODO: 未來可用於 Token 黑名單持久化、Session 共享、快取等
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 環境設定
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # JWT（SECRET_KEY 生產環境必須從環境變數設定）
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-CHANGE-THIS-IN-PRODUCTION-min-32-chars-required-for-security"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # 資料庫連線池配置
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))

    # 快取 TTL 配置（秒）
    CACHE_TTL_SENSITIVE_WORDS: int = int(os.getenv("CACHE_TTL_SENSITIVE_WORDS", "300"))  # 5 分鐘

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 驗證 SECRET_KEY（生產環境強制要求）
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY.startswith("dev-secret-key"):
                raise ValueError(
                    "SECRET_KEY must be set in environment variables for production. "
                    "Generate one with: openssl rand -hex 32"
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    f"SECRET_KEY must be at least 32 characters long. "
                    f"Current length: {len(self.SECRET_KEY)}"
                )


settings = Settings()
