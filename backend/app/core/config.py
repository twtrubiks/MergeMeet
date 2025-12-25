"""應用程式配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """應用程式設定"""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # 專案資訊
    PROJECT_NAME: str = "MergeMeet"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # 資料庫（必須從環境變數設定）
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://mergemeet:YOUR_DB_PASSWORD_HERE@localhost:5432/mergemeet"
    )

    # Redis（用於 Token 黑名單、登入限制、信任分數、內容審核快取）
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 環境設定
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # JWT（SECRET_KEY 生產環境必須從環境變數設定）
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-CHANGE-THIS-IN-PRODUCTION-min-32-chars-required-for-security"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "180"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

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

    # WebSocket 訊息限制
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "2000"))  # 即時聊天訊息長度限制

    # Email 服務配置 (開發環境使用 Mailpit)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "1025"))
    SMTP_USER: str = os.getenv("SMTP_USER", "mergemeet")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@mergemeet.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "MergeMeet")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "false").lower() == "true"

    # 前端 URL (用於生成重置密碼鏈接)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # 密碼重置 Token 有效期 (分鐘)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Cookie 安全配置（HttpOnly Cookie 防止 XSS 攻擊）
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")  # 開發: lax, 生產: strict
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", "")  # 空字串表示當前域名
    COOKIE_PATH: str = "/"

    # CSRF Token 配置
    CSRF_TOKEN_LENGTH: int = 32

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
