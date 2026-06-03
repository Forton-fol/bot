from functools import lru_cache
import os
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_database_url() -> str:
    """
    Railway: внутренний postgres.railway.internal иногда не резолвится у сервиса бота.
    По умолчанию при наличии DATABASE_PUBLIC_URL используем его.
    """
    internal = os.getenv("DATABASE_URL", "").strip()
    public = os.getenv("DATABASE_PUBLIC_URL", "").strip()
    private = os.getenv("DATABASE_PRIVATE_URL", "").strip()
    prefer_public = os.getenv("PREFER_PUBLIC_DATABASE", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    ordered: list[str] = []
    if prefer_public:
        if public:
            ordered.append(public)
        if internal:
            ordered.append(internal)
        if private:
            ordered.append(private)
    else:
        if internal:
            ordered.append(internal)
        if private:
            ordered.append(private)
        if public:
            ordered.append(public)

    for url in ordered:
        if url:
            return url
    return ""


def _ensure_ssl(url: str) -> str:
    """Публичный прокси Railway (*.rlwy.net) требует SSL."""
    if "rlwy.net" not in url and "railway.app" not in url:
        return url
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "sslmode" in query or "ssl" in query:
        return url
    query["ssl"] = ["require"]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = ""
    admin_telegram_ids: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="Europe/Moscow", alias="TIMEZONE")

    @model_validator(mode="before")
    @classmethod
    def inject_database_url(cls, data: dict) -> dict:
        if not data.get("database_url"):
            resolved = _resolve_database_url()
            if resolved:
                data["database_url"] = resolved
        return data

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not value:
            resolved = _resolve_database_url()
            if not resolved:
                return value
            value = resolved
        if isinstance(value, str) and value.startswith("postgresql://"):
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return _ensure_ssl(value)

    @property
    def database_host(self) -> str:
        try:
            return urlparse(self.database_url).hostname or "?"
        except Exception:
            return "?"

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
        if not _resolve_database_url():
            missing.append(
                "DATABASE_URL или DATABASE_PUBLIC_URL (Reference из Postgres на сервис бота)"
            )
        hint = (
            "Задайте переменные в сервисе БОТА на Railway: " + ", ".join(missing)
            if missing
            else str(exc)
        )
        raise RuntimeError(hint) from exc
