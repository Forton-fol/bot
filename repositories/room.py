from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.room import Room


class RoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self) -> list[Room]:
        result = await self.session.execute(select(Room).order_by(Room.name))
        return list(result.scalars().all())

    async def get_by_id(self, room_id: int) -> Room | None:
        result = await self.session.execute(select(Room).where(Room.id == room_id))
        return result.scalar_one_or_none()

    async def create(self, name: str, address: str) -> Room:
        room = Room(name=name, address=address)
        self.session.add(room)
        await self.session.flush()
        return room

    async def ensure_defaults(self) -> None:
        defaults = [
            ("Кабинет 1", "ул. Примерная, д. 1"),
            ("Кабинет 2", "ул. Примерная, д. 1"),
        ]
        existing = await self.get_all()
        if existing:
            return
        for name, address in defaults:
            await self.create(name, address)
