from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from models.enums import RoleName


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")

    @staticmethod
    def default_roles() -> list[dict[str, str]]:
        return [
            {"name": RoleName.PLAYER.value},
            {"name": RoleName.MASTER.value},
            {"name": RoleName.ADMIN.value},
        ]


from models.user import User  # noqa: E402, F401
