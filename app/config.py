from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # No default for secret_key: the app refuses to start without it.
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite:///./test.db"

    # Redis is optional. Leave REDIS_URL empty to use an in-memory cache instead.
    redis_url: Optional[str] = None
    cache_ttl_seconds: int = 30

    # Background jobs (Celery). Empty = use REDIS_URL if set, else a local folder (.celery/).
    celery_broker_url: Optional[str] = None
    celery_always_eager: bool = False  # True = run tasks immediately (used by tests)

    # Optional: a URL that receives a POST when a match finishes.
    webhook_url: Optional[str] = None

    # Rate limits: allowed requests per window.
    rate_limit_window_seconds: int = 60
    login_rate_limit: int = 5
    register_rate_limit: int = 10
    write_rate_limit: int = 30

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
