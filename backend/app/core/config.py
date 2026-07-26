"""Application settings — every value env-overridable, validated at boot."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Shantranj API"
    env: str = "dev"  # dev | test | prod
    debug: bool = True
    secret_key: str = "change-me-in-prod"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    database_url: str = "postgresql+asyncpg://study:study_dev@timescaledb:5432/study"
    redis_url: str = "redis://redis:6379/0"
    engine_url: str = "http://engine:9000"

    # Auth
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 7
    cookie_secure: bool = False  # True behind TLS in prod

    # Google OAuth (empty = feature disabled, endpoints answer 503)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    # Rate limiting
    rate_limit_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
