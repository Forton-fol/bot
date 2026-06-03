from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.enums import GameStatus, ParticipantStatus
from models.game import Game
from models.user import User


def game_card_kb(
    game: Game,
    user: User | None,
    participant_status: str | None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if game.status in (GameStatus.CANCELLED.value, GameStatus.ARCHIVED.value):
        builder.button(text="Игра недоступна", callback_data=f"noop:{game.id}")
        builder.adjust(1)
        return builder.as_markup()

    if participant_status == ParticipantStatus.REGISTERED.value:
        builder.button(
            text="❌ Отменить запись",
            callback_data=f"unregister:{game.id}",
        )
    elif participant_status == ParticipantStatus.WAITLIST.value:
        builder.button(
            text="❌ Выйти из листа ожидания",
            callback_data=f"unregister:{game.id}",
        )
    elif game.status == GameStatus.FULL.value or game.free_slots <= 0:
        if participant_status is None:
            builder.button(
                text="📋 В лист ожидания",
                callback_data=f"register:{game.id}",
            )
        else:
            builder.button(text="Мест нет", callback_data=f"noop:{game.id}")
    else:
        builder.button(
            text="✅ Записаться",
            callback_data=f"register:{game.id}",
        )

    builder.button(text="🔄 Обновить", callback_data=f"refresh:{game.id}")
    builder.adjust(1)
    return builder.as_markup()


def games_list_kb(games: list[Game], prefix: str = "show") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for game in games:
        date_str = game.game_date.strftime("%d.%m")
        builder.button(
            text=f"{game.title} ({date_str})",
            callback_data=f"{prefix}:{game.id}",
        )
    builder.adjust(1)
    return builder.as_markup()
