import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class ActionLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            uid = event.from_user.id if event.from_user else None
            logger.info("message user=%s text=%s", uid, event.text[:100])
        elif isinstance(event, CallbackQuery) and event.data:
            uid = event.from_user.id if event.from_user else None
            logger.info("callback user=%s data=%s", uid, event.data)
        return await handler(event, data)
