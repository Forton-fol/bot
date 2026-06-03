import logging

from aiogram import BaseMiddleware
from aiogram.types import ErrorEvent, Message, TelegramObject, Update

logger = logging.getLogger(__name__)


class ErrorNotifyMiddleware(BaseMiddleware):
    """Логирует ошибки и по возможности отвечает пользователю."""

    async def __call__(self, handler, event: TelegramObject, data: dict):
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Unhandled error while processing update")
            raise


async def on_error(event: ErrorEvent) -> None:
    logger.exception(
        "Handler error: %s",
        event.exception,
        exc_info=event.exception,
    )
    update = event.update
    chat_id = None
    if isinstance(update, Update):
        if update.message:
            chat_id = update.message.chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id
    if chat_id and event.bot:
        try:
            await event.bot.send_message(
                chat_id,
                "⚠️ Произошла ошибка. Попробуйте позже или напишите /start.",
            )
        except Exception:
            logger.exception("Failed to send error message to user")
