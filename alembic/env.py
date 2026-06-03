"""
Alembic: синхронный psycopg2.
На Railway пробует URL по очереди: internal → public (см. bot.config.get_database_url_candidates).
"""
import logging
import time
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from bot.config import get_database_url_candidates
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


def _to_psycopg2_url(async_url: str) -> str:
    url = async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    parsed = urlparse(url)
    host = parsed.hostname or ""
    query = parse_qs(parsed.query)

    for key in ("ssl", "sslmode"):
        query.pop(key, None)

    # Внутренняя сеть Railway — без SSL
    if "railway.internal" in host:
        pass
    elif "rlwy.net" in host or "railway.app" in host:
        # Публичный прокси — только с SSL
        query["sslmode"] = ["require"]

    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def _migrate_with_url(psycopg_url: str) -> None:
    host = urlparse(psycopg_url).hostname
    logger.info("Alembic trying host=%s", host)
    engine = create_engine(
        psycopg_url,
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 30},
    )
    try:
        with engine.connect() as connection:
            do_run_migrations(connection)
    finally:
        engine.dispose()


def run_migrations_online() -> None:
    candidates = get_database_url_candidates()
    if not candidates:
        raise RuntimeError("No DATABASE_URL configured")

    errors: list[str] = []
    for async_url in candidates:
        psycopg_url = _to_psycopg2_url(async_url)
        for attempt in range(1, 4):
            try:
                _migrate_with_url(psycopg_url)
                logger.info("Alembic OK on host=%s", urlparse(psycopg_url).hostname)
                return
            except Exception as exc:
                msg = f"{urlparse(psycopg_url).hostname} attempt {attempt}: {exc}"
                logger.warning(msg)
                errors.append(msg)
                time.sleep(2 * attempt)

    raise RuntimeError("All database URLs failed:\n" + "\n".join(errors))


def run_migrations_offline() -> None:
    candidates = get_database_url_candidates()
    if not candidates:
        raise RuntimeError("No DATABASE_URL configured")
    url = _to_psycopg2_url(candidates[0])
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
