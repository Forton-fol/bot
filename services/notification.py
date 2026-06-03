from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from models.enums import NotificationType, ParticipantStatus
from models.game import Game
from models.notification import Notification
from repositories.notification import NotificationRepository


class NotificationService:
    REMINDER_TEXTS = {
        NotificationType.REMINDER_1_DAY.value: "Игра начнётся через 1 день.\nИгра: {title}",
        NotificationType.REMINDER_12_HOURS.value: "Игра начнётся через 12 часов.\nИгра: {title}",
        NotificationType.REMINDER_1_HOUR.value: "Игра начнётся через 1 час.\nИгра: {title}",
        NotificationType.GAME_START.value: "Игра начинается!\nИгра: {title}",
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)
        self.settings = get_settings()

    def _tz(self) -> ZoneInfo:
        return ZoneInfo(self.settings.timezone)

    def _game_starts_at(self, game: Game) -> datetime:
        naive = game.starts_at
        return naive.replace(tzinfo=self._tz())

    async def schedule_for_game(self, game: Game) -> None:
        await self.notifications.delete_for_game(game.id)
        starts = self._game_starts_at(game)
        schedule = [
            (NotificationType.REMINDER_1_DAY.value, starts - timedelta(days=1)),
            (NotificationType.REMINDER_12_HOURS.value, starts - timedelta(hours=12)),
            (NotificationType.REMINDER_1_HOUR.value, starts - timedelta(hours=1)),
            (NotificationType.GAME_START.value, starts),
        ]
        now = datetime.now(self._tz())
        for ntype, at in schedule:
            if at > now:
                await self.notifications.create(game.id, ntype, at)

    async def send_pending(self, bot: Bot) -> int:
        now = datetime.now(self._tz())
        pending = await self.notifications.get_pending(now)
        sent_count = 0
        for notification in pending:
            game = notification.game
            if not game:
                await self.notifications.mark_sent(notification)
                continue
            text = self.REMINDER_TEXTS.get(
                notification.notification_type,
                f"Напоминание об игре: {game.title}",
            ).format(title=game.title)

            for participant in game.participants:
                if participant.status != ParticipantStatus.REGISTERED.value:
                    continue
                user = participant.user
                if not user:
                    continue
                try:
                    await bot.send_message(user.telegram_id, text)
                except Exception:
                    pass

            await self.notifications.mark_sent(notification)
            sent_count += 1
        return sent_count
