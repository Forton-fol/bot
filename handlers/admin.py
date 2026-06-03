from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.states import AdminStates
from keyboards.admin import admin_game_actions_kb, admin_games_kb, admin_menu_kb, role_select_kb
from keyboards.common import cancel_kb
from models.enums import RoleName
from models.user import User
from repositories.game import GameRepository
from repositories.user import UserRepository
from services.excel_export import ExcelExportService
from services.game import GameService
from services.points import PointsService
from services.user import UserService

router = Router(name="admin")


def _is_admin(user: User) -> bool:
    return user.role_name == RoleName.ADMIN.value


@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🛠 <b>Панель администратора</b>",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:registrations")
async def cb_registrations(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    from models.enums import ParticipantStatus
    from models.game_participant import GameParticipant
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(GameParticipant)
        .options(
            selectinload(GameParticipant.user),
            selectinload(GameParticipant.game),
        )
        .where(GameParticipant.status == ParticipantStatus.REGISTERED.value)
        .order_by(GameParticipant.registered_at.desc())
        .limit(50)
    )
    parts = list(result.scalars().all())
    if not parts:
        await callback.message.answer("Записей пока нет.")  # type: ignore[union-attr]
        await callback.answer()
        return
    lines = ["📋 <b>Последние записи</b>\n"]
    for p in parts:
        g = p.game
        u = p.user
        if g and u:
            lines.append(
                f"• {u.full_name} → {g.title} ({g.game_date.strftime('%d.%m')})"
            )
    await callback.message.answer("\n".join(lines[:40]))  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_stats(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    repo = GameRepository(session)
    stats = await repo.get_statistics()
    users = UserRepository(session)
    masters = await users.count_masters()
    text = (
        "📊 <b>Статистика клуба</b>\n\n"
        f"🎲 Всего игр: {stats['total_games']}\n"
        f"🟢 Активных: {stats['active_games']}\n"
        f"📦 В архиве: {stats['archived_games']}\n"
        f"📝 Записей: {stats['total_registrations']}\n"
        f"🧙 Мастеров: {masters}\n"
    )
    await callback.message.answer(text)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "admin:export")
async def cb_export(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    service = ExcelExportService(session)
    path = await service.export_statistics("/tmp/exports")
    await callback.message.answer_document(  # type: ignore[union-attr]
        FSInputFile(path),
        caption="📥 Статистика клуба",
    )
    await callback.answer("Экспорт готов")


@router.callback_query(F.data == "admin:games")
async def cb_games(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    repo = GameRepository(session)
    games = await repo.list_all_for_admin()
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🎲 <b>Управление играми</b>",
        reply_markup=admin_games_kb(games),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:game:"))
async def cb_game_detail(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    game_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    repo = GameRepository(session)
    game = await repo.get_by_id(game_id)
    if not game:
        await callback.answer("Не найдено", show_alert=True)
        return
    from bot.utils import format_game_card

    await callback.message.edit_text(  # type: ignore[union-attr]
        format_game_card(game),
        reply_markup=admin_game_actions_kb(game_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:cancel_game:"))
async def cb_cancel_game(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    game_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    repo = GameRepository(session)
    game = await repo.get_by_id(game_id)
    if not game:
        await callback.answer("Не найдено", show_alert=True)
        return
    service = GameService(session)
    await service.cancel_game(user, game)
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"🚫 Игра «{game.title}» отменена."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:edit:"))
async def cb_edit_game(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    game_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    await state.set_state(AdminStates.edit_game_value)
    await state.update_data(edit_game_id=game_id, edit_field="title")
    await callback.message.answer(  # type: ignore[union-attr]
        "Введите новое название игры:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.edit_game_value)
async def st_edit_value(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    if not _is_admin(user):
        return
    data = await state.get_data()
    game_id = data.get("edit_game_id")
    repo = GameRepository(session)
    game = await repo.get_by_id(game_id)
    if not game:
        await message.answer("Игра не найдена")
        await state.clear()
        return
    service = GameService(session)
    await service.update_game(game, title=message.text.strip())
    await state.clear()
    await message.answer(f"✅ Игра обновлена: «{game.title}»")


@router.callback_query(F.data == "admin:set_role")
async def cb_set_role(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.set_role_telegram_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "Введите Telegram ID пользователя:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.set_role_telegram_id)
async def st_set_role_id(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой Telegram ID:")
        return
    repo = UserRepository(session)
    target = await repo.get_by_telegram_id(tg_id)
    if not target:
        await message.answer("Пользователь не найден. Он должен написать боту /start.")
        return
    await state.clear()
    await message.answer(
        f"Выберите роль для {target.full_name}:",
        reply_markup=role_select_kb(target.id),
    )


@router.callback_query(F.data.startswith("admin:role:"))
async def cb_apply_role(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split(":")  # type: ignore[union-attr]
    target_id = int(parts[2])
    role_name = parts[3]
    repo = UserRepository(session)
    target = await repo.get_by_id(target_id)
    if not target:
        await callback.answer("Не найден", show_alert=True)
        return
    service = UserService(session)
    await service.set_role(user, target, role_name)
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"✅ Роль {role_name} назначена пользователю {target.full_name}"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:create_master")
async def cb_create_master(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.create_master_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "Введите Telegram ID будущего мастера:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.create_master_id)
async def st_create_master(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой Telegram ID:")
        return
    service = UserService(session)
    target = await service.promote_to_master(user, tg_id)
    await state.clear()
    if not target:
        await message.answer("Пользователь не найден. Попросите его написать /start.")
        return
    await message.answer(f"✅ {target.full_name} назначен мастером.")


@router.callback_query(F.data == "admin:points_add")
async def cb_points_add(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.update_data(points_mode="add")
    await state.set_state(AdminStates.points_user_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "Введите Telegram ID игрока:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:points_sub")
async def cb_points_sub(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    if not _is_admin(user):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.update_data(points_mode="sub")
    await state.set_state(AdminStates.points_user_id)
    await callback.message.answer(  # type: ignore[union-attr]
        "Введите Telegram ID игрока:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.points_user_id)
async def st_points_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой Telegram ID:")
        return
    repo = UserRepository(session)
    target = await repo.get_by_telegram_id(tg_id)
    if not target:
        await message.answer("Пользователь не найден.")
        return
    await state.update_data(points_target_id=target.id)
    await state.set_state(AdminStates.points_amount)
    await message.answer("Введите количество баллов:")


@router.message(AdminStates.points_amount)
async def st_points_amount(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("Введите целое число:")
        return
    data = await state.get_data()
    mode = data.get("points_mode", "add")
    if mode == "sub":
        amount = -abs(amount)
    else:
        amount = abs(amount)

    repo = UserRepository(session)
    target = await repo.get_by_id(data["points_target_id"])
    if not target:
        await message.answer("Пользователь не найден.")
        await state.clear()
        return

    service = PointsService(session)
    total = await service.manual_adjust(user, target, amount)
    await state.clear()
    await message.answer(
        f"✅ Баллы обновлены.\n{target.full_name}: <b>{total}</b> баллов."
    )
