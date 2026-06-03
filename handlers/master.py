from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.states import CreateGameStates
from keyboards.common import cancel_kb, skip_kb
from models.enums import RoleName
from models.user import User
from services.game import GameService

router = Router(name="master")


def _check_master(user: User) -> bool:
    return user.role_name in (RoleName.MASTER.value, RoleName.ADMIN.value)


async def _publish_game(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    data = await state.get_data()
    service = GameService(session)
    game = await service.create_game(user, data)
    await state.clear()
    await message.answer(
        f"✅ Игра «{game.title}» опубликована и доступна игрокам!"
    )


@router.message(Command("create_game"))
async def cmd_create_game(message: Message, user: User, state: FSMContext) -> None:
    if not _check_master(user):
        await message.answer("⛔ Создание игр доступно мастерам и администраторам.")
        return
    await state.set_state(CreateGameStates.title)
    await message.answer(
        "🎲 <b>Создание игры</b>\n\nВведите название игры:",
        reply_markup=cancel_kb(),
    )


@router.message(CreateGameStates.title)
async def st_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateGameStates.image)
    await message.answer(
        "Отправьте изображение для карточки (или пропустите):",
        reply_markup=skip_kb(),
    )


@router.message(CreateGameStates.image, F.photo)
async def st_image(message: Message, state: FSMContext) -> None:
    await state.update_data(image_file_id=message.photo[-1].file_id)
    await state.set_state(CreateGameStates.game_date)
    await message.answer("Введите дату игры (ДД.ММ.ГГГГ):")


@router.callback_query(CreateGameStates.image, F.data == "skip")
async def st_image_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateGameStates.game_date)
    await callback.message.answer("Введите дату игры (ДД.ММ.ГГГГ):")  # type: ignore[union-attr]
    await callback.answer()


@router.message(CreateGameStates.game_date)
async def st_date(message: Message, state: FSMContext) -> None:
    try:
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ:")
        return
    await state.update_data(game_date=d)
    await state.set_state(CreateGameStates.game_time)
    await message.answer("Введите время (ЧЧ:ММ):")


@router.message(CreateGameStates.game_time)
async def st_time(message: Message, state: FSMContext) -> None:
    try:
        t = datetime.strptime(message.text.strip(), "%H:%M").time()
    except ValueError:
        await message.answer("Неверный формат. Используйте ЧЧ:ММ:")
        return
    await state.update_data(game_time=t)
    await state.set_state(CreateGameStates.system_name)
    await message.answer("Введите игровую систему (например, D&D 5e):")


@router.message(CreateGameStates.system_name)
async def st_system(message: Message, state: FSMContext) -> None:
    await state.update_data(system_name=message.text.strip())
    await state.set_state(CreateGameStates.session_type)
    await message.answer("Введите тип партии (ваншот, кампания и т.д.):")


@router.message(CreateGameStates.session_type)
async def st_session(message: Message, state: FSMContext) -> None:
    await state.update_data(session_type=message.text.strip())
    await state.set_state(CreateGameStates.player_level)
    await message.answer("Введите уровень опыта игроков:")


@router.message(CreateGameStates.player_level)
async def st_player_level(message: Message, state: FSMContext) -> None:
    await state.update_data(player_level=message.text.strip())
    await state.set_state(CreateGameStates.character_level)
    await message.answer("Введите уровень персонажей:")


@router.message(CreateGameStates.character_level)
async def st_char_level(message: Message, state: FSMContext) -> None:
    await state.update_data(character_level=message.text.strip())
    await state.set_state(CreateGameStates.max_slots)
    await message.answer("Введите количество мест (число):")


@router.message(CreateGameStates.max_slots)
async def st_slots(message: Message, state: FSMContext) -> None:
    try:
        slots = int(message.text.strip())
        if slots < 1:
            raise ValueError
    except ValueError:
        await message.answer("Введите целое число больше 0:")
        return
    await state.update_data(max_slots=slots)
    await state.set_state(CreateGameStates.price)
    await message.answer("Введите стоимость (например, 500 ₽ или бесплатно):")


@router.message(CreateGameStates.price)
async def st_price(message: Message, state: FSMContext) -> None:
    await state.update_data(price=message.text.strip())
    await state.set_state(CreateGameStates.room)
    await message.answer("Введите номер кабинета:")


@router.message(CreateGameStates.room)
async def st_room(message: Message, state: FSMContext) -> None:
    await state.update_data(room_text=message.text.strip())
    await state.set_state(CreateGameStates.address)
    await message.answer("Введите адрес проведения:")


@router.message(CreateGameStates.address)
async def st_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    await state.set_state(CreateGameStates.description)
    await message.answer("Введите описание игры:")


@router.message(CreateGameStates.description)
async def st_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(CreateGameStates.notes)
    await message.answer(
        "Введите дополнительные заметки (или пропустите):",
        reply_markup=skip_kb(),
    )


@router.message(CreateGameStates.notes)
async def st_notes(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    await state.update_data(notes=message.text.strip())
    await _publish_game(message, state, session, user)


@router.callback_query(CreateGameStates.notes, F.data == "skip")
async def st_notes_skip(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    await state.update_data(notes=None)
    await _publish_game(callback.message, state, session, user)  # type: ignore[arg-type]
    await callback.answer()
