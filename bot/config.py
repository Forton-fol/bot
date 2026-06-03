from functools import lru_cache
import logging
import os
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _is_valid_pg_url(url: str) -> bool:
    if not url or url.startswith("${"):
        return False
    if "@db:" in url or "@db/" in url:
        return False
    return url.startswith("postgresql://") or url.startswith("postgresql+asyncpg://")


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


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return _ensure_ssl(url)


def _resolve_database_url() -> str:
    internal = os.getenv("DATABASE_URL", "").strip()
    public = os.getenv("DATABASE_PUBLIC_URL", "").strip()
    private = os.getenv("DATABASE_PRIVATE_URL", "").strip()
    on_railway = bool(os.getenv("RAILWAY_ENVIRONMENT"))

    if not _is_valid_pg_url(internal):
        internal = ""
    if not _is_valid_pg_url(public):
        public = ""
    if not _is_valid_pg_url(private):
        private = ""

    if on_railway:
        if public:
            logger.info("Railway: using DATABASE_PUBLIC_URL")
            return _normalize_url(public)
        raise RuntimeError(
            "На Railway в сервисе BOT нет DATABASE_PUBLIC_URL. "
            "Variables → New Variable → Add Reference → Postgres → DATABASE_PUBLIC_URL. "
            "Только DATABASE_URL (postgres.railway.internal) у вас не работает — таймаут в логах."
        )

    prefer_public = os.getenv("PREFER_PUBLIC_DATABASE", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    ordered: list[str] = []
    if prefer_public:
        ordered.extend([public, internal, private])
    else:
        ordered.extend([internal, private, public])

    for url in ordered:
        if url:
            return _normalize_url(url)
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
        if not os.getenv("DATABASE_PUBLIC_URL") and os.getenv("RAILWAY_ENVIRONMENT"):
            missing.append("DATABASE_PUBLIC_URL (Reference на Postgres)")
        elif not _resolve_database_url():
            missing.append("DATABASE_URL")
        hint = (
            "Задайте переменные в сервисе БОТА на Railway: " + ", ".join(missing)
            if missing
            else str(exc)
        )
        raise RuntimeError(hint) from exc
