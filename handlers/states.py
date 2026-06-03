from aiogram.fsm.state import State, StatesGroup


class CreateGameStates(StatesGroup):
    title = State()
    image = State()
    game_date = State()
    game_time = State()
    system_name = State()
    session_type = State()
    player_level = State()
    character_level = State()
    max_slots = State()
    price = State()
    room = State()
    address = State()
    description = State()
    notes = State()


class AdminStates(StatesGroup):
    set_role_telegram_id = State()
    create_master_id = State()
    points_user_id = State()
    points_amount = State()
    edit_game_value = State()
