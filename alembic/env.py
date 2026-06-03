"""
Alembic: только СИНХРОННЫЙ движок (psycopg2).

Async env.py + asyncio.run() + asyncpg на Railway даёт Connection reset при SSL.
Бот работает через asyncpg (database/session.py), миграции — отдельно через psycopg2.
"""
import logging
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from bot.config import get_settings
from database.base import Base

import models.action_log  # noqa: F401
import models.game  # noqa: F401
import models.game_participant  # noqa: F401
import models.notification  # noqa: F401
import models.points_history  # noqa: F401
import models.role  # noqa: F401
import models.room  # noqa: F401
import models.user  # noqa: F401

logger = logging.getLogger(__name__)
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()


def _sync_migration_url(async_url: str) -> str:
    """postgresql+asyncpg://... → postgresql+psycopg2://... + sslmode для Railway."""
    url = async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if not url.startswith("postgresql"):
        url = f"postgresql+psycopg2://{url.split('://', 1)[-1]}"

    if "rlwy.net" in url or "railway.app" in url:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query["sslmode"] = ["require"]
        url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
    return url


def run_migrations_offline() -> None:
    url = _sync_migration_url(settings.database_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _sync_migration_url(settings.database_url)
    host = urlparse(url).hostname
    logger.info("Alembic sync migrate → host=%s", host)

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 60},
    )
    try:
        with connectable.connect() as connection:
            do_run_migrations(connection)
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
