from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.game import Game
from models.user import User


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Назначить роль", callback_data="admin:set_role")
    builder.button(text="🎭 Создать мастера", callback_data="admin:create_master")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="📋 Все записи", callback_data="admin:registrations")
    builder.button(text="📥 Экспорт Excel", callback_data="admin:export")
    builder.button(text="🎲 Все игры", callback_data="admin:games")
    builder.button(text="⭐ Начислить баллы", callback_data="admin:points_add")
    builder.button(text="➖ Списать баллы", callback_data="admin:points_sub")
    builder.adjust(2)
    return builder.as_markup()


def admin_games_kb(games: list[Game]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in games:
        builder.button(
            text=f"{g.title} [{g.status}]",
            callback_data=f"admin:game:{g.id}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:menu"))
    return builder.as_markup()


def admin_game_actions_kb(game_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"admin:edit:{game_id}")
    builder.button(text="🚫 Отменить игру", callback_data=f"admin:cancel_game:{game_id}")
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:games"))
    return builder.as_markup()


def role_select_kb(target_user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for role in ("player", "master", "admin"):
        builder.button(
            text=role.capitalize(),
            callback_data=f"admin:role:{target_user_id}:{role}",
        )
    builder.adjust(3)
    return builder.as_markup()


def master_list_kb(masters: list[User]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in masters:
        builder.button(
            text=m.full_name,
            callback_data=f"admin:master_info:{m.telegram_id}",
        )
    builder.adjust(1)
    return builder.as_markup()
