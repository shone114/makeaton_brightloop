import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Brightloop Subscription Management System"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "brightloop-super-secret-key-hackathon-2026-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours for seamless demoing
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Defaults to SQLite async for instant local dev & testing, or accepts PostgreSQL connection string
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./brightloop.db")
    
    # Resend email API key
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    
    # CORS origins
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://brightloop-demo.vercel.app",
        "*"
    ]

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")


settings = Settings()

