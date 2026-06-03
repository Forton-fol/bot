from models.enums import GameStatus, ParticipantStatus
from models.game import Game


def format_game_card(game: Game, participant_status: str | None = None) -> str:
    master_name = game.master.full_name if game.master else "—"
    room_name = game.room_text or (game.room.name if game.room else "—")
    waitlist_note = ""
    if participant_status == ParticipantStatus.WAITLIST.value:
        waitlist_note = "\n\n📋 <b>Вы в листе ожидания</b>"
    elif participant_status == ParticipantStatus.REGISTERED.value:
        waitlist_note = "\n\n✅ <b>Вы записаны</b>"

    status_emoji = {
        GameStatus.OPEN.value: "🟢",
        GameStatus.FULL.value: "🔴",
        GameStatus.IN_PROGRESS.value: "▶️",
        GameStatus.ARCHIVED.value: "📦",
        GameStatus.CANCELLED.value: "🚫",
        GameStatus.DRAFT.value: "📝",
        GameStatus.FINISHED.value: "✅",
    }.get(game.status, "🎲")

    notes_block = f"\n\n📌 <b>Заметки:</b>\n{game.notes}" if game.notes else ""

    return (
        f"{status_emoji} <b>{game.title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>Дата:</b> {game.game_date.strftime('%d.%m.%Y')}\n"
        f"🕐 <b>Время:</b> {game.game_time.strftime('%H:%M')}\n"
        f"🧙 <b>Мастер:</b> {master_name}\n"
        f"🎲 <b>Система:</b> {game.system_name}\n"
        f"📖 <b>Тип партии:</b> {game.session_type}\n"
        f"👥 <b>Уровень игроков:</b> {game.player_level}\n"
        f"⚔️ <b>Уровень персонажей:</b> {game.character_level}\n"
        f"🪑 <b>Свободно мест:</b> {game.free_slots} из {game.max_slots}\n"
        f"📍 <b>Адрес:</b> {game.address}\n"
        f"🚪 <b>Кабинет:</b> {room_name}\n"
        f"💰 <b>Стоимость:</b> {game.price}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Описание:</b>\n{game.description}"
        f"{notes_block}"
        f"{waitlist_note}"
    )


def format_profile(user, recent_games: list) -> str:
    games_lines = ""
    if recent_games:
        games_lines = "\n".join(
            f"  • {g.title} ({g.game_date.strftime('%d.%m.%Y')})"
            for g in recent_games[:5]
        )
    else:
        games_lines = "  — пока нет"

    return (
        f"👤 <b>Профиль игрока</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 <b>Имя:</b> {user.full_name}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"🎮 <b>Посещённых игр:</b> {user.games_attended}\n"
        f"⭐ <b>Баллы:</b> {user.points}\n"
        f"🏷 <b>Роль:</b> {user.role_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📜 <b>Последние игры:</b>\n{games_lines}"
    )


def format_leaderboard(users: list) -> str:
    if not users:
        return "🏆 Рейтинг пуст."
    lines = ["🏆 <b>Рейтинг игроков</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for idx, u in enumerate(users, start=1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
        lines.append(f"{medal} {u.full_name} — <b>{u.points}</b> баллов")
    return "\n".join(lines)
