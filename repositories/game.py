from datetime import date, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.enums import GameStatus, ParticipantStatus
from models.game import Game
from models.game_participant import GameParticipant
from models.user import User


class GameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(self):
        return select(Game).options(
            selectinload(Game.master).selectinload(User.role),
            selectinload(Game.room),
            selectinload(Game.participants).selectinload(GameParticipant.user),
        )

    async def get_by_id(self, game_id: int) -> Game | None:
        result = await self.session.execute(
            self._base_query().where(Game.id == game_id)
        )
        return result.scalar_one_or_none()

    async def get_upcoming(
        self,
        limit: int = 10,
        statuses: list[str] | None = None,
    ) -> list[Game]:
        if statuses is None:
            statuses = [GameStatus.OPEN.value, GameStatus.FULL.value]
        today = date.today()
        result = await self.session.execute(
            self._base_query()
            .where(
                Game.status.in_(statuses),
                or_(
                    Game.game_date > today,
                    and_(Game.game_date == today),
                ),
            )
            .order_by(Game.game_date, Game.game_time)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def get_user_registrations(self, user_id: int) -> list[Game]:
        result = await self.session.execute(
            self._base_query()
            .join(GameParticipant)
            .where(
                GameParticipant.user_id == user_id,
                GameParticipant.status.in_([
                    ParticipantStatus.REGISTERED.value,
                    ParticipantStatus.WAITLIST.value,
                ]),
                Game.status.in_([
                    GameStatus.OPEN.value,
                    GameStatus.FULL.value,
                    GameStatus.IN_PROGRESS.value,
                ]),
            )
            .order_by(Game.game_date, Game.game_time)
        )
        return list(result.scalars().unique().all())

    async def create(self, **kwargs) -> Game:
        game = Game(**kwargs)
        self.session.add(game)
        await self.session.flush()
        return await self.get_by_id(game.id)  # type: ignore[return-value]

    async def update(self, game: Game, **kwargs) -> Game:
        for key, value in kwargs.items():
            setattr(game, key, value)
        await self.session.flush()
        return game

    async def get_participant(
        self,
        game_id: int,
        user_id: int,
    ) -> GameParticipant | None:
        result = await self.session.execute(
            select(GameParticipant).where(
                GameParticipant.game_id == game_id,
                GameParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_participant(
        self,
        game_id: int,
        user_id: int,
        status: str,
    ) -> GameParticipant:
        participant = GameParticipant(
            game_id=game_id,
            user_id=user_id,
            status=status,
        )
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def count_registered(self, game_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.status == ParticipantStatus.REGISTERED.value,
            )
        )
        return result.scalar_one()

    async def count_waitlist(self, game_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.status == ParticipantStatus.WAITLIST.value,
            )
        )
        return result.scalar_one()

    async def get_waitlist_position(self, game_id: int, user_id: int) -> int | None:
        result = await self.session.execute(
            select(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.status == ParticipantStatus.WAITLIST.value,
            )
            .order_by(GameParticipant.registered_at)
        )
        participants = list(result.scalars().all())
        for idx, p in enumerate(participants, start=1):
            if p.user_id == user_id:
                return idx
        return None

    async def get_games_to_start(self, now: datetime) -> list[Game]:
        result = await self.session.execute(
            self._base_query().where(
                Game.status.in_([GameStatus.OPEN.value, GameStatus.FULL.value]),
                Game.game_date == now.date(),
            )
        )
        games = list(result.scalars().unique().all())
        return [g for g in games if g.starts_at <= now]

    async def get_games_to_finish(self, now: datetime, duration_hours: int = 4) -> list[Game]:
        result = await self.session.execute(
            self._base_query().where(Game.status == GameStatus.IN_PROGRESS.value)
        )
        games = list(result.scalars().unique().all())
        from datetime import timedelta

        return [
            g
            for g in games
            if g.started_at and g.started_at + timedelta(hours=duration_hours) <= now
        ]

    async def get_statistics(self) -> dict:
        total_games = await self.session.scalar(select(func.count()).select_from(Game))
        active = await self.session.scalar(
            select(func.count()).select_from(Game).where(
                Game.status.in_([
                    GameStatus.OPEN.value,
                    GameStatus.FULL.value,
                    GameStatus.IN_PROGRESS.value,
                ])
            )
        )
        archived = await self.session.scalar(
            select(func.count()).select_from(Game).where(
                Game.status == GameStatus.ARCHIVED.value
            )
        )
        participants = await self.session.scalar(
            select(func.count()).select_from(GameParticipant).where(
                GameParticipant.status == ParticipantStatus.REGISTERED.value
            )
        )
        return {
            "total_games": total_games or 0,
            "active_games": active or 0,
            "archived_games": archived or 0,
            "total_registrations": participants or 0,
        }

    async def list_all_for_admin(self, limit: int = 50) -> list[Game]:
        result = await self.session.execute(
            self._base_query().order_by(Game.game_date.desc()).limit(limit)
        )
        return list(result.scalars().unique().all())
