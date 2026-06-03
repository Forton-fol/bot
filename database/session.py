from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import get_database_url_candidates, get_settings
from bot.db_connect import asyncpg_connect_args
from database.base import Base

_settings = get_settings()
_db_url = _settings.database_url

engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=asyncpg_connect_args(_db_url),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def all_configured_db_hosts() -> list[str]:
    return [urlparse(u).hostname or "?" for u in get_database_url_candidates()]
