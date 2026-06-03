from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from models.enums import ParticipantStatus


class GameParticipant(Base):
    __tablename__ = "game_participants"
    __table_args__ = (
        UniqueConstraint("game_id", "user_id", name="uq_game_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=ParticipantStatus.REGISTERED.value,
        server_default=ParticipantStatus.REGISTERED.value,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    game: Mapped["Game"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship(back_populates="participations")


from models.game import Game  # noqa: E402
from models.user import User  # noqa: E402
