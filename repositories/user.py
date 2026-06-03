from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.enums import ParticipantStatus, RoleName
from models.game import Game
from models.game_participant import GameParticipant
from models.role import Role
from models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None,
        role_id: int,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            role_id=role_id,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user, ["role"])
        return user

    async def update_role(self, user: User, role_id: int) -> User:
        user.role_id = role_id
        await self.session.flush()
        await self.session.refresh(user, ["role"])
        return user

    async def add_points(self, user: User, amount: int) -> User:
        user.points += amount
        await self.session.flush()
        return user

    async def increment_attended(self, user: User) -> None:
        user.games_attended += 1
        await self.session.flush()

    async def get_leaderboard(self, limit: int = 20) -> list[User]:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.role))
            .order_by(User.points.desc(), User.games_attended.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_games(self, user_id: int, limit: int = 5) -> list[Game]:
        result = await self.session.execute(
            select(Game)
            .join(GameParticipant, GameParticipant.game_id == Game.id)
            .options(selectinload(Game.master).selectinload(User.role))
            .where(
                GameParticipant.user_id == user_id,
                GameParticipant.status == ParticipantStatus.REGISTERED.value,
            )
            .order_by(Game.game_date.desc(), Game.game_time.desc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def count_masters(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .join(Role)
            .where(Role.name == RoleName.MASTER.value)
        )
        return result.scalar_one()

    async def list_by_role(self, role_name: str) -> list[User]:
        result = await self.session.execute(
            select(User)
            .join(Role)
            .options(selectinload(User.role))
            .where(Role.name == role_name)
            .order_by(User.full_name)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[User]:
        result = await self.session.execute(
            select(User).options(selectinload(User.role)).order_by(User.full_name)
        )
        return list(result.scalars().all())
