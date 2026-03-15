"""應用程式配置"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """應用程式設定"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # 專案資訊
    PROJECT_NAME: str = "MergeMeet"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # 資料庫（必須從環境變數設定）
    DATABASE_URL: str = (
        "postgresql+asyncpg://mergemeet:YOUR_DB_PASSWORD_HERE@localhost:5432/mergemeet"
    )

    # Redis（用於 Token 黑名單、登入限制、信任分數、內容審核快取）
    # ⚠️ 正式環境請更換為安全密碼
    REDIS_URL: str = "redis://:mergemeet_redis123@localhost:6379/0"

    # 環境設定
    ENVIRONMENT: str = "development"

    # JWT（SECRET_KEY 生產環境必須從環境變數設定）
    SECRET_KEY: str = "dev-secret-key-CHANGE-THIS-IN-PRODUCTION-min-32-chars-required-for-security"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # 資料庫連線池配置
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # 快取 TTL 配置（秒）
    CACHE_TTL_SENSITIVE_WORDS: int = 300  # 5 分鐘

    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    # 檔案上傳
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_DIR: str = "uploads"

    # WebSocket 訊息限制
    MAX_MESSAGE_LENGTH: int = 2000  # 即時聊天訊息長度限制

    # Email 服務配置 (開發環境使用 Mailpit)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = "mergemeet"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@mergemeet.com"
    SMTP_FROM_NAME: str = "MergeMeet"
    SMTP_TLS: bool = False

    # 前端 URL (用於生成重置密碼鏈接)
    FRONTEND_URL: str = "http://localhost:5173"

    # 密碼重置 Token 有效期 (分鐘)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Cookie 安全配置（HttpOnly Cookie 防止 XSS 攻擊）
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"  # 開發: lax, 生產: strict
    COOKIE_DOMAIN: str = ""  # 空字串表示當前域名
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
