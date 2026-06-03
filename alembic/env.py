import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from bot.config import get_settings
from bot.db_connect import asyncpg_connect_args
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


def run_migrations_offline() -> None:
    url = settings.database_url
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


async def run_async_migrations() -> None:
    """Прямой AsyncEngine из настроек — не из placeholder alembic.ini."""
    logger.info("Alembic: connect to %s", settings.database_host)
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,
        connect_args=asyncpg_connect_args(settings.database_url),
    )
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """
    Вызывается из bot/main.py ДО asyncio.run(main()) — event loop ещё нет.
    Только asyncio.run(), без get_running_loop() и без вложенных loop.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
