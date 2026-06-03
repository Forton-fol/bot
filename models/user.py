from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    games_attended: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    role: Mapped["Role"] = relationship(back_populates="users")
    participations: Mapped[list["GameParticipant"]] = relationship(back_populates="user")
    points_history: Mapped[list["PointsHistory"]] = relationship(back_populates="user")
    mastered_games: Mapped[list["Game"]] = relationship(back_populates="master")

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else "player"


from models.game import Game  # noqa: E402
from models.game_participant import GameParticipant  # noqa: E402
from models.points_history import PointsHistory  # noqa: E402
from models.role import Role  # noqa: E402
