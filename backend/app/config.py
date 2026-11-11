import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "SirenSync Patient Authentication API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:////Users/shambhavisingh/Desktop/SirenSync/database/sirensync.db"
    )
    SESSION_COOKIE_NAME: str = "sirensync_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    # Cloudflare Turnstile dummy testing secret key (always passes when used with dummy token)
    TURNSTILE_SECRET_KEY: str = os.getenv(
        "TURNSTILE_SECRET_KEY", 
        "1x0000000000000000000000000000000AA"
    )
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000"
    ]
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = "lax"

settings = Settings()
