from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils import format_profile
from handlers.player import send_upcoming_games
from keyboards.admin import admin_menu_kb
from keyboards.common import main_menu_kb
from models.enums import RoleName
from models.user import User
from repositories.user import UserRepository
from services.user import UserService

router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, user: User) -> None:
    await message.answer(
        f"Добро пожаловать в НРИ-клуб, {user.full_name}! 🎲\n\n"
        "Здесь вы можете записываться на игры, получать напоминания "
        "и копить баллы за посещения.",
        reply_markup=main_menu_kb(),
    )
    await send_upcoming_games(message, session, user)


@router.message(Command("help"))
async def cmd_help(message: Message, user: User) -> None:
    text = (
        "📖 <b>Справка</b>\n\n"
        "/start — ближайшие игры\n"
        "/profile — ваш профиль\n"
        "/my_games — ваши записи\n"
        "/games — список игр\n"
        "/rating — рейтинг по баллам\n"
    )
    if user.role_name in (RoleName.MASTER.value, RoleName.ADMIN.value):
        text += "/create_game — создать игру (мастер)\n"
    if user.role_name == RoleName.ADMIN.value:
        text += "/admin — панель администратора\n"
    await message.answer(text)


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message, session: AsyncSession, user: User) -> None:
    service = UserService(session)
    data = await service.get_profile_data(user)
    await message.answer(format_profile(data["user"], data["recent_games"]))


@router.message(Command("rating"))
@router.message(F.text == "🏆 Рейтинг")
async def cmd_rating(message: Message, session: AsyncSession) -> None:
    from bot.utils import format_leaderboard

    repo = UserRepository(session)
    leaders = await repo.get_leaderboard(20)
    await message.answer(format_leaderboard(leaders))


@router.message(Command("admin"))
async def cmd_admin(message: Message, user: User) -> None:
    if user.role_name != RoleName.ADMIN.value:
        await message.answer("⛔ Доступ только для администраторов.")
        return
    await message.answer("🛠 <b>Панель администратора</b>", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "back_menu")
async def cb_back_menu(callback: CallbackQuery) -> None:
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.answer()
