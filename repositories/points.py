from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.points_history import PointsHistory


class PointsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_record(
        self,
        user_id: int,
        amount: int,
        reason: str,
        game_id: int | None = None,
        created_by_id: int | None = None,
        note: str | None = None,
    ) -> PointsHistory:
        record = PointsHistory(
            user_id=user_id,
            amount=amount,
            reason=reason,
            game_id=game_id,
            created_by_id=created_by_id,
            note=note,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_user_history(self, user_id: int, limit: int = 20) -> list[PointsHistory]:
        result = await self.session.execute(
            select(PointsHistory)
            .where(PointsHistory.user_id == user_id)
            .order_by(PointsHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_for_export(self) -> list[PointsHistory]:
        result = await self.session.execute(
            select(PointsHistory)
            .options(selectinload(PointsHistory.user))
            .order_by(PointsHistory.created_at.desc())
        )
        return list(result.scalars().all())
