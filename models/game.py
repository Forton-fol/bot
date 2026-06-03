from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from models.enums import GameStatus


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    image_file_id: Mapped[str | None] = mapped_column(String(512))
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    game_time: Mapped[time] = mapped_column(Time, nullable=False)
    system_name: Mapped[str] = mapped_column(String(128), nullable=False)
    session_type: Mapped[str] = mapped_column(String(128), nullable=False)
    player_level: Mapped[str] = mapped_column(String(128), nullable=False)
    character_level: Mapped[str] = mapped_column(String(128), nullable=False)
    max_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    occupied_slots: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    price: Mapped[str] = mapped_column(String(64), nullable=False)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    room_text: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32),
        default=GameStatus.DRAFT.value,
        server_default=GameStatus.DRAFT.value,
        index=True,
    )
    master_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    master: Mapped["User"] = relationship(back_populates="mastered_games")
    room: Mapped["Room | None"] = relationship(back_populates="games")
    participants: Mapped[list["GameParticipant"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )

    @property
    def free_slots(self) -> int:
        return max(0, self.max_slots - self.occupied_slots)

    @property
    def starts_at(self) -> datetime:
        return datetime.combine(self.game_date, self.game_time)


from models.game_participant import GameParticipant  # noqa: E402
from models.notification import Notification  # noqa: E402
from models.room import Room  # noqa: E402
from models.user import User  # noqa: E402
