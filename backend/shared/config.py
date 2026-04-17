"""
Application configuration loaded from the .env file.
All services import settings from here:
    from shared.config import settings
"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:ankush@database-1.czsy4cckqbwv.ap-south-2.rds.amazonaws.com:5432/postgres"
    DATABASE_URL_SYNC: str = "postgresql://postgres:ankush@database-1.czsy4cckqbwv.ap-south-2.rds.amazonaws.com:5432/postgres"

    REDIS_URL: str = "redis://rediscluster.mycatz.ng.0001.aps2.cache.amazonaws.com:6379/0"

    JWT_SECRET_KEY: str = "zylo-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    OPENWEATHERMAP_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    MSG91_AUTH_KEY: str = ""
    MSG91_OTP_TEMPLATE_ID: str = ""
    MSG91_OTP_LENGTH: int = 6
    MSG91_OTP_EXPIRY_MINUTES: int = 5

    OTP_PROVIDER: str = "dev"
    OTP_LENGTH: int = 6
    OTP_EXPIRY_SECONDS: int = 300
    OTP_DEV_BYPASS_ENABLED: bool = True
    OTP_DEV_BYPASS_CODE: str = "123456"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme"

    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "Zylo"
    APP_VERSION: str = "1.0.0"
    CORS_ALLOWED_ORIGINS: str = ""

    ML_SERVICE_URL: str = "http://ml:8001"
    NEBIUS_API_KEY: str = ""
    NEBIUS_BASE_URL: str = "https://api.tokenfactory.us-central1.nebius.com/v1/"
    NEBIUS_MODEL: str = "moonshotai/Kimi-K2.5-fast"
    NEBIUS_TIMEOUT_SECONDS: int = 20
    NEBIUS_MAX_RETRIES: int = 1

    UPLOAD_DIR: str = "./uploads"

    # SS Code, 2020 — Engagement Rule
    # Riders must complete this many days on-platform before purchasing a policy.
    # Set to 90 for production (SS Code mandate). 0 for demo/hackathon.
    MIN_ENGAGEMENT_DAYS: int = 0

    # Pool Sustainability — IRDAI Guideline
    # Target Benefit-Cost Ratio. Payouts should be ≤ this fraction of premiums.
    TARGET_BCR: float = 0.65

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False

        return False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
