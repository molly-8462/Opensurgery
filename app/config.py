from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Change this one value to update user-visible backend branding everywhere.
    site_name: str = "OpenSurgery"
    database_url: str = "postgresql+psycopg://opensurgery:opensurgery@localhost:5432/opensurgery"
    secret_key: str = "development-only-change-me-before-deployment"
    access_token_minutes: int = 30
    cookie_secure: bool = False
    media_root: Path = Path("var/media")
    public_base_url: str = "http://127.0.0.1:8000"
    smtp_host: str = "smtp.resend.com"
    smtp_port: int = 587
    smtp_username: str = "resend"
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
