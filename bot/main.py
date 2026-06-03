import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from middlewares.errors import on_error
from repositories.role import RoleRepository
from repositories.room import RoomRepository


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


def run_migrations() -> None:
    """Синхронный запуск Alembic — только до asyncio.run(main())."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    logging.getLogger(__name__).info("Database migrations applied")


async def seed_data() -> None:
    from database.session import async_session_factory

    async with async_session_factory() as session:
        roles = RoleRepository(session)
        rooms = RoomRepository(session)
        await roles.ensure_defaults()
        await rooms.ensure_defaults()
        await session.commit()


async def main() -> None:
    from database.session import async_session_factory  # noqa: F401
    from handlers import setup_routers
    from middlewares import ActionLoggingMiddleware, DbSessionMiddleware, UserMiddleware
    from scheduler import setup_scheduler

    settings = get_settings()
    log = logging.getLogger(__name__)

    await seed_data()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.errors.register(on_error)

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(UserMiddleware())
    dp.update.middleware(ActionLoggingMiddleware())

    dp.include_router(setup_routers())

    me = await bot.get_me()
    log.info("Bot @%s (id=%s) ready", me.username, me.id)

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Webhook removed, starting polling")

    scheduler = setup_scheduler(bot)
    scheduler.start()

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    import os

    settings = get_settings()
    setup_logging(settings.log_level)
    log = logging.getLogger(__name__)
    log.info("DATABASE_PUBLIC_URL задана: %s", bool(os.getenv("DATABASE_PUBLIC_URL")))
    log.info("DATABASE_URL задана: %s", bool(os.getenv("DATABASE_URL")))
    log.info("Подключение к БД, host: %s", settings.database_host)

    # 1) Миграции — синхронно, без running event loop
    try:
        run_migrations()
    except Exception:
        log.exception("Alembic migration failed")
        raise

    # 2) Бот — один event loop
    asyncio.run(main())
