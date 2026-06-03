from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils import format_game_card
from keyboards.common import main_menu_kb
from keyboards.game import game_card_kb, games_list_kb
from models.enums import GameStatus
from models.game import Game
from models.user import User
from repositories.game import GameRepository
from services.game import GameService


router = Router(name="player")


async def send_game_card(
    target: Message | CallbackQuery,
    game: Game,
    user: User,
    session: AsyncSession,
    *,
    edit: bool = False,
) -> None:
    game_service = GameService(session)
    status = await game_service.get_participant_status(game, user)
    text = format_game_card(game, status)
    kb = game_card_kb(game, user, status)

    if game.image_file_id:
        if edit and isinstance(target, CallbackQuery):
            try:
                await target.message.delete()  # type: ignore[union-attr]
            except Exception:
                pass
        msg_target = target if isinstance(target, Message) else target.message
        await msg_target.answer_photo(  # type: ignore[union-attr]
            photo=game.image_file_id,
            caption=text,
            reply_markup=kb,
        )
    else:
        if edit and isinstance(target, CallbackQuery) and target.message:
            await target.message.edit_text(text, reply_markup=kb)
        else:
            msg = target if isinstance(target, Message) else target.message
            await msg.answer(text, reply_markup=kb)  # type: ignore[union-attr]


async def send_upcoming_games(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    repo = GameRepository(session)
    games = await repo.get_upcoming(limit=10)
    if not games:
        await message.answer(
            "📭 Ближайших игр пока нет. Загляните позже!",
            reply_markup=main_menu_kb(),
        )
        return
    await message.answer(
        f"🎲 <b>Ближайшие игры</b> ({len(games)}):",
        reply_markup=games_list_kb(games, "show"),
    )


@router.message(Command("games"))
@router.message(F.text == "🎲 Ближайшие игры")
async def cmd_games(message: Message, session: AsyncSession, user: User) -> None:
    await send_upcoming_games(message, session, user)


@router.message(Command("my_games"))
@router.message(F.text == "📋 Мои записи")
async def cmd_my_games(message: Message, session: AsyncSession, user: User) -> None:
    repo = GameRepository(session)
    games = await repo.get_user_registrations(user.id)
    if not games:
        await message.answer("У вас пока нет активных записей.")
        return
    await message.answer(
        "📋 <b>Ваши записи:</b>",
        reply_markup=games_list_kb(games, "show"),
    )


@router.callback_query(F.data.startswith("show:"))
async def cb_show_game(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    game_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    repo = GameRepository(session)
    game = await repo.get_by_id(game_id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    await send_game_card(callback, game, user, session)
    await callback.answer()


@router.callback_query(F.data.startswith("register:"))
async def cb_register(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    game_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    repo = GameRepository(session)
    game = await repo.get_by_id(game_id)
    if not game or game.status == GameStatus.CANCELLED.value:
        await callback.answer("Игра недоступна", show_alert=True)
        return

    service = GameService(session)
    result, game = await service.register(user, game)

    messages = {
        "registered": "✅ Вы записаны на игру!",
        "waitlist": "📋 Вы добавлены в лист ожидания.",
        "already_registered": "Вы уже записаны.",
        "already_waitlist": "Вы уже в листе ожидания.",
    }
    await callback.answer(messages.get(result, "Готово"), show_alert=True)
    await send_game_card(callback, game, user, session, edit=True)


@router.callback_query(F.data.startswith("unregister:"))
async def cb_unregister(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    game_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    repo = GameRepository(session)
    game = await repo.get_by_id(game_id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return

    service = GameService(session)
    result, game = await service.cancel_registration(user, game)
    msg = "Запись отменена." if result == "cancelled" else "Вы не были записаны."
    await callback.answer(msg, show_alert=True)
    await send_game_card(callback, game, user, session, edit=True)


@router.callback_query(F.data.startswith("refresh:"))
async def cb_refresh(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    game_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    repo = GameRepository(session)
    game = await repo.get_by_id(game_id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    await send_game_card(callback, game, user, session, edit=True)
    await callback.answer("Обновлено")


@router.callback_query(F.data.startswith("noop:"))
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer("Мест нет", show_alert=True)
