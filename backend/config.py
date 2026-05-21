"""Application configuration loaded from environment (.env supported)."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load .env from this folder (next to config.py), not the shell cwd.
_BACKEND_DIR = Path(__file__).resolve().parent
_ENV_PATH = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # mysql | sqlite — use sqlite for local dev without a MySQL server
    db_backend: str = Field(default="mysql", validation_alias="DB_BACKEND")

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "medical_assistant"

    sqlite_path: str = Field(default="medical_assistant.db", validation_alias="SQLITE_PATH")

    jwt_secret_key: str = "dev-only-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    admin_seed_name: str = Field(default="Admin", validation_alias="ADMIN_SEED_NAME")
    admin_seed_email: str = Field(
        default="dishantdishanth1234@gmail.com",
        validation_alias="ADMIN_SEED_EMAIL",
    )
    admin_seed_password: str = Field(default="dishanthmnaik", validation_alias="ADMIN_SEED_PASSWORD")

    # Email OTP (optional SMTP). If host is empty, OTP is only logged server-side.
    smtp_host: str = Field(default="", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", validation_alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")

    otp_expire_minutes: int = Field(default=15, validation_alias="OTP_EXPIRE_MINUTES")

    # Ephemeral user activity: chats, health logs, appointments, reports are purged after this many hours.
    user_data_retention_hours: int = Field(default=24, validation_alias="USER_DATA_RETENTION_HOURS")
    data_retention_purge_interval_minutes: int = Field(
        default=30, validation_alias="DATA_RETENTION_PURGE_INTERVAL_MINUTES"
    )


settings = Settings()


def is_sqlite() -> bool:
    return (settings.db_backend or "mysql").lower().strip() == "sqlite"
