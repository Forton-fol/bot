from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from repositories.action_log import ActionLogRepository
from repositories.points import PointsRepository
from repositories.user import UserRepository


class PointsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.points = PointsRepository(session)
        self.users = UserRepository(session)
        self.logs = ActionLogRepository(session)

    async def award_game_participation(
        self,
        user: User,
        game_id: int,
        game_title: str,
    ) -> int:
        await self.users.add_points(user, 1)
        await self.users.increment_attended(user)
        await self.points.add_record(
            user_id=user.id,
            amount=1,
            reason=f"Участие в игре «{game_title}»",
            game_id=game_id,
        )
        return user.points

    async def manual_adjust(
        self,
        admin: User,
        target: User,
        amount: int,
        note: str | None = None,
    ) -> int:
        if amount == 0:
            return target.points
        if amount > 0:
            await self.users.add_points(target, amount)
            reason = "Ручное начисление"
            action = "points_add"
        else:
            target.points = max(0, target.points + amount)
            await self.session.flush()
            reason = "Ручное списание"
            action = "points_deduct"

        await self.points.add_record(
            user_id=target.id,
            amount=amount,
            reason=reason,
            created_by_id=admin.id,
            note=note,
        )
        await self.logs.log(
            action,
            admin.telegram_id,
            f"target={target.telegram_id}, amount={amount}",
        )
        return target.points
