from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from services.user import UserService


def _extract_tg_user(event: TelegramObject):
    if isinstance(event, Message):
        return event.from_user
    if isinstance(event, CallbackQuery):
        return event.from_user
    if isinstance(event, Update):
        for attr in ("message", "edited_message", "callback_query", "inline_query"):
            inner = getattr(event, attr, None)
            if inner is not None:
                if isinstance(inner, Message):
                    return inner.from_user
                if isinstance(inner, CallbackQuery):
                    return inner.from_user
                if hasattr(inner, "from_user"):
                    return inner.from_user
    if getattr(event, "message", None):
        return event.message.from_user
    return None


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

        tg_user = _extract_tg_user(event)
        if tg_user:
            is_admin = tg_user.id in settings.admin_ids
            user = await user_service.get_or_create(
                telegram_id=tg_user.id,
                full_name=tg_user.full_name or "Игрок",
                username=tg_user.username,
                is_admin_config=is_admin,
            )
            data["user"] = user
            data["user_service"] = user_service

        return await handler(event, data)
