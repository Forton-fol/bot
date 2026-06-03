from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.game import Game
from models.game_participant import GameParticipant
from models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        game_id: int,
        notification_type: str,
        scheduled_at: datetime,
    ) -> Notification:
        notification = Notification(
            game_id=game_id,
            notification_type=notification_type,
            scheduled_at=scheduled_at,
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_pending(self, now: datetime) -> list[Notification]:
        result = await self.session.execute(
            select(Notification)
            .options(
                selectinload(Notification.game)
                .selectinload(Game.master),
                selectinload(Notification.game)
                .selectinload(Game.participants)
                .selectinload(GameParticipant.user),
            )
            .where(Notification.sent.is_(False), Notification.scheduled_at <= now)
        )
        return list(result.scalars().all())

    async def mark_sent(self, notification: Notification) -> None:
        notification.sent = True
        notification.sent_at = datetime.now().astimezone()
        await self.session.flush()

    async def delete_for_game(self, game_id: int) -> None:
        result = await self.session.execute(
            select(Notification).where(Notification.game_id == game_id)
        )
        for n in result.scalars().all():
            await self.session.delete(n)
        await self.session.flush()
