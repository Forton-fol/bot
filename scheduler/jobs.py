import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from database.session import async_session_factory
from models.enums import GameStatus, ParticipantStatus
from repositories.game import GameRepository
from services.game import GameService
from services.notification import NotificationService
from services.points import PointsService

logger = logging.getLogger(__name__)


async def job_send_notifications(bot: Bot) -> None:
    async with async_session_factory() as session:
        service = NotificationService(session)
        count = await service.send_pending(bot)
        await session.commit()
        if count:
            logger.info("Sent %d notifications", count)


async def job_start_games(bot: Bot) -> None:
    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.timezone))
    async with async_session_factory() as session:
        repo = GameRepository(session)
        service = GameService(session)
        games = await repo.get_games_to_start(now)
        for game in games:
            await service.start_game(game)
            for p in game.participants:
                if p.status != ParticipantStatus.REGISTERED.value:
                    continue
                if p.user:
                    try:
                        await bot.send_message(
                            p.user.telegram_id,
                            f"Игра начинается!\nИгра: {game.title}",
                        )
                    except Exception:
                        pass
        await session.commit()
        if games:
            logger.info("Started %d games", len(games))


async def job_finish_games(bot: Bot) -> None:
    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.timezone))
    async with async_session_factory() as session:
        await _finish_and_award(session, bot, now)
        await session.commit()


async def _finish_and_award(
    session: AsyncSession,
    bot: Bot,
    now: datetime,
) -> None:
    repo = GameRepository(session)
    game_service = GameService(session)
    points_service = PointsService(session)
    games = await repo.get_games_to_finish(now)
    for game in games:
        game.status = GameStatus.FINISHED.value
        await session.flush()
        await game_service.finish_and_archive(game)

        archive_msg = (
            f'Игра "{game.title}" прошла и была перенесена в архив.'
        )
        for participant in game.participants:
            if participant.status != ParticipantStatus.REGISTERED.value:
                continue
            user = participant.user
            if not user:
                continue
            total = await points_service.award_game_participation(
                user, game.id, game.title
            )
            try:
                await bot.send_message(
                    user.telegram_id,
                    archive_msg,
                )
                await bot.send_message(
                    user.telegram_id,
                    f"Вы получили 1 балл за участие в игре.\n"
                    f"Всего баллов: {total}",
                )
            except Exception:
                pass
        logger.info("Finished and archived game %s", game.id)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=get_settings().timezone)
    scheduler.add_job(
        job_send_notifications,
        "interval",
        minutes=1,
        args=[bot],
        id="notifications",
        replace_existing=True,
    )
    scheduler.add_job(
        job_start_games,
        "interval",
        minutes=1,
        args=[bot],
        id="start_games",
        replace_existing=True,
    )
    scheduler.add_job(
        job_finish_games,
        "interval",
        minutes=5,
        args=[bot],
        id="finish_games",
        replace_existing=True,
    )
    return scheduler
