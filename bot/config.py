from functools import lru_cache
import logging
import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _is_valid_pg_url(url: str) -> bool:
    if not url or url.startswith("${"):
        return False
    if "@db:" in url or "@db/" in url:
        return False
    return url.startswith("postgresql://") or url.startswith("postgresql+asyncpg://")


def _strip_ssl_query(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("ssl", "sslmode"):
        query.pop(key, None)
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return _strip_ssl_query(url)


def get_database_url_candidates() -> list[str]:
    """
    Список URL для попытки подключения (порядок важен).
    На Railway: сначала внутренний DATABASE_URL (без SSL), потом публичный прокси.
    """
    internal = os.getenv("DATABASE_URL", "").strip()
    public = os.getenv("DATABASE_PUBLIC_URL", "").strip()
    private = os.getenv("DATABASE_PRIVATE_URL", "").strip()
    on_railway = bool(os.getenv("RAILWAY_ENVIRONMENT"))

    valid = {
        "internal": _normalize_url(internal) if _is_valid_pg_url(internal) else "",
        "private": _normalize_url(private) if _is_valid_pg_url(private) else "",
        "public": _normalize_url(public) if _is_valid_pg_url(public) else "",
    }

    if on_railway:
        order = ["internal", "private", "public"]
    else:
        prefer_public = os.getenv("PREFER_PUBLIC_DATABASE", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        order = (
            ["public", "internal", "private"]
            if prefer_public
            else ["internal", "private", "public"]
        )

    seen: set[str] = set()
    result: list[str] = []
    for key in order:
        url = valid.get(key, "")
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _resolve_database_url() -> str:
    candidates = get_database_url_candidates()
    on_railway = bool(os.getenv("RAILWAY_ENVIRONMENT"))

    if candidates:
        host = urlparse(candidates[0]).hostname or "?"
        logger.info("Primary database host: %s", host)
        return candidates[0]

    if on_railway:
        raise RuntimeError(
            "На Railway в сервисе BOT нужен Reference: Postgres → DATABASE_URL. "
            "Опционально DATABASE_PUBLIC_URL как запасной."
        )
    return ""


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
        data["database_url"] = _resolve_database_url()
        return data

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not value:
            return _resolve_database_url()
        return _normalize_url(value)

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
        if not get_database_url_candidates():
            missing.append("DATABASE_URL (Reference на Postgres)")
        hint = (
            "Задайте переменные в сервисе БОТА на Railway: " + ", ".join(missing)
            if missing
            else str(exc)
        )
        raise RuntimeError(hint) from exc
