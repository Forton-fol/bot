from sqlalchemy.ext.asyncio import AsyncSession

from models.action_log import ActionLog


class ActionLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        action: str,
        telegram_id: int | None = None,
        details: str | None = None,
    ) -> None:
        self.session.add(
            ActionLog(
                telegram_id=telegram_id,
                action=action,
                details=details,
            )
        )
        await self.session.flush()
