from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import RoleName
from models.user import User
from repositories.action_log import ActionLogRepository
from repositories.role import RoleRepository
from repositories.user import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.logs = ActionLogRepository(session)

    async def get_or_create(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None,
        is_admin_config: bool = False,
    ) -> User:
        user = await self.users.get_by_telegram_id(telegram_id)
        if user:
            if user.full_name != full_name or user.username != username:
                user.full_name = full_name
                user.username = username
                await self.session.flush()
            if is_admin_config and user.role_name != RoleName.ADMIN.value:
                admin_role = await self.roles.get_by_name(RoleName.ADMIN.value)
                if admin_role:
                    await self.users.update_role(user, admin_role.id)
            return user

        await self.roles.ensure_defaults()
        if is_admin_config:
            role = await self.roles.get_by_name(RoleName.ADMIN.value)
        else:
            role = await self.roles.get_by_name(RoleName.PLAYER.value)
        assert role is not None

        user = await self.users.create(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            role_id=role.id,
        )
        await self.logs.log("user_registered", telegram_id, full_name)
        return user

    async def promote_to_master(self, admin: User, target_telegram_id: int) -> User | None:
        target = await self.users.get_by_telegram_id(target_telegram_id)
        if not target:
            return None
        role = await self.roles.get_by_name(RoleName.MASTER.value)
        assert role is not None
        await self.users.update_role(target, role.id)
        await self.logs.log(
            "promote_master",
            admin.telegram_id,
            f"target={target_telegram_id}",
        )
        return target

    async def set_role(self, admin: User, target: User, role_name: str) -> User:
        role = await self.roles.get_by_name(role_name)
        if not role:
            raise ValueError(f"Unknown role: {role_name}")
        await self.users.update_role(target, role.id)
        await self.logs.log(
            "set_role",
            admin.telegram_id,
            f"target={target.telegram_id}, role={role_name}",
        )
        return target

    async def get_profile_data(self, user: User) -> dict:
        recent = await self.users.get_recent_games(user.id)
        return {
            "user": user,
            "recent_games": recent,
        }
