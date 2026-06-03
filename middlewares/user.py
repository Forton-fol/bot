from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from services.user import UserService


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]
        user_service = UserService(session)
        settings = get_settings()

        tg_user = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            tg_user = event.from_user
        elif getattr(event, "message", None) and event.message.from_user:
            tg_user = event.message.from_user

        if tg_user:
            is_admin = tg_user.id in settings.admin_ids
            user = await user_service.get_or_create(
                telegram_id=tg_user.id,
                full_name=tg_user.full_name,
                username=tg_user.username,
                is_admin_config=is_admin,
            )
            data["user"] = user
            data["user_service"] = user_service

        return await handler(event, data)
