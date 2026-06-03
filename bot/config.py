from functools import lru_cache
import os

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(
        validation_alias=AliasChoices("DATABASE_URL", "DATABASE_PUBLIC_URL"),
    )
    admin_telegram_ids: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="Europe/Moscow", alias="TIMEZONE")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Railway отдаёт postgresql:// — для SQLAlchemy async нужен asyncpg."""
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def admin_ids(self) -> list[int]:
        if not self.admin_telegram_ids.strip():
            return []
        ids: list[int] = []
        for raw in self.admin_telegram_ids.split(","):
            token = raw.strip().lstrip("@")
            if token.isdigit():
                ids.append(int(token))
        return ids


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:
        missing = []
        if not os.getenv("BOT_TOKEN"):
            missing.append("BOT_TOKEN")
        if not os.getenv("DATABASE_URL") and not os.getenv("DATABASE_PUBLIC_URL"):
            missing.append("DATABASE_URL (или DATABASE_PUBLIC_URL)")
        hint = (
            "Задайте переменные в сервисе БОТА на Railway (не в Postgres): "
            + ", ".join(missing)
            if missing
            else str(exc)
        )
        raise RuntimeError(hint) from exc
