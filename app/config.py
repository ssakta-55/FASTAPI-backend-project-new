from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # No default for secret_key: the app refuses to start without it.
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite:///./test.db"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
