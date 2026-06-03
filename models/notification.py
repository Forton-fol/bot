from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    game: Mapped["Game"] = relationship(back_populates="notifications")


from models.game import Game  # noqa: E402
