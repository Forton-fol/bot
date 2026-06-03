import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from database.session import async_session_factory
from handlers import setup_routers
from middlewares import ActionLoggingMiddleware, DbSessionMiddleware, UserMiddleware
from repositories.role import RoleRepository
from repositories.room import RoomRepository
from scheduler import setup_scheduler


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


async def seed_data() -> None:
    async with async_session_factory() as session:
        roles = RoleRepository(session)
        rooms = RoomRepository(session)
        await roles.ensure_defaults()
        await rooms.ensure_defaults()
        await session.commit()


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    await seed_data()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(UserMiddleware())
    dp.update.middleware(ActionLoggingMiddleware())

    dp.include_router(setup_routers())

    scheduler = setup_scheduler(bot)
    scheduler.start()

    logging.getLogger(__name__).info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
