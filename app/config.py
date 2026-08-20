from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://opensurgery:opensurgery@localhost:5432/opensurgery"
    secret_key: str = "development-only-change-me-before-deployment"
    access_token_minutes: int = 30
    cookie_secure: bool = False
    media_root: Path = Path("var/media")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
