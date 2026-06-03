from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎲 Ближайшие игры")
    builder.button(text="📋 Мои записи")
    builder.button(text="👤 Профиль")
    builder.button(text="🏆 Рейтинг")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
            ]
        ]
    )


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="back_menu")
    return builder.as_markup()
