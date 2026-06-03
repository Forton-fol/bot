from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.role import Role


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Role]:
        result = await self.session.execute(select(Role).order_by(Role.id))
        return list(result.scalars().all())

    async def ensure_defaults(self) -> None:
        for item in Role.default_roles():
            existing = await self.get_by_name(item["name"])
            if not existing:
                self.session.add(Role(name=item["name"]))
        await self.session.flush()
