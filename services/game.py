from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from models.enums import GameStatus, ParticipantStatus
from models.game import Game
from models.user import User
from repositories.action_log import ActionLogRepository
from repositories.game import GameRepository
from repositories.room import RoomRepository
from services.notification import NotificationService


class GameService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.games = GameRepository(session)
        self.rooms = RoomRepository(session)
        self.logs = ActionLogRepository(session)
        self.notifications = NotificationService(session)
        self.settings = get_settings()

    async def create_game(self, master: User, data: dict) -> Game:
        room = None
        if data.get("room_id"):
            room = await self.rooms.get_by_id(data["room_id"])
        address = data.get("address") or (room.address if room else "Уточняется")
        game = await self.games.create(
            title=data["title"],
            image_file_id=data.get("image_file_id"),
            game_date=data["game_date"],
            game_time=data["game_time"],
            system_name=data["system_name"],
            session_type=data["session_type"],
            player_level=data["player_level"],
            character_level=data["character_level"],
            max_slots=data["max_slots"],
            price=data["price"],
            room_id=data.get("room_id"),
            room_text=data.get("room_text"),
            address=address,
            description=data["description"],
            notes=data.get("notes"),
            status=GameStatus.OPEN.value,
            master_id=master.id,
        )
        await self.notifications.schedule_for_game(game)
        await self.logs.log("game_created", master.telegram_id, f"game_id={game.id}")
        return game

    async def register(self, user: User, game: Game) -> tuple[str, Game]:
        existing = await self.games.get_participant(game.id, user.id)
        if existing:
            if existing.status == ParticipantStatus.REGISTERED.value:
                return "already_registered", game
            if existing.status == ParticipantStatus.WAITLIST.value:
                return "already_waitlist", game

        registered_count = await self.games.count_registered(game.id)
        if registered_count < game.max_slots:
            await self.games.add_participant(
                game.id, user.id, ParticipantStatus.REGISTERED.value
            )
            game.occupied_slots = registered_count + 1
            if game.occupied_slots >= game.max_slots:
                game.status = GameStatus.FULL.value
            await self.session.flush()
            game = await self.games.get_by_id(game.id)  # type: ignore[assignment]
            await self.logs.log(
                "game_register", user.telegram_id, f"game_id={game.id}"
            )
            return "registered", game  # type: ignore[return-value]

        await self.games.add_participant(
            game.id, user.id, ParticipantStatus.WAITLIST.value
        )
        await self.logs.log("game_waitlist", user.telegram_id, f"game_id={game.id}")
        game = await self.games.get_by_id(game.id)  # type: ignore[assignment]
        return "waitlist", game  # type: ignore[return-value]

    async def cancel_registration(self, user: User, game: Game) -> tuple[str, Game]:
        participant = await self.games.get_participant(game.id, user.id)
        if not participant or participant.status == ParticipantStatus.CANCELLED.value:
            return "not_registered", game

        was_registered = participant.status == ParticipantStatus.REGISTERED.value
        participant.status = ParticipantStatus.CANCELLED.value

        if was_registered:
            game.occupied_slots = max(0, game.occupied_slots - 1)
            if game.status == GameStatus.FULL.value:
                game.status = GameStatus.OPEN.value
            await self._promote_from_waitlist(game)

        await self.session.flush()
        game = await self.games.get_by_id(game.id)  # type: ignore[assignment]
        await self.logs.log(
            "game_unregister", user.telegram_id, f"game_id={game.id}"
        )
        return "cancelled", game  # type: ignore[return-value]

    async def _promote_from_waitlist(self, game: Game) -> None:
        from sqlalchemy import select

        from models.game_participant import GameParticipant

        result = await self.session.execute(
            select(GameParticipant)
            .where(
                GameParticipant.game_id == game.id,
                GameParticipant.status == ParticipantStatus.WAITLIST.value,
            )
            .order_by(GameParticipant.registered_at)
            .limit(1)
        )
        next_p = result.scalar_one_or_none()
        if not next_p:
            return
        registered = await self.games.count_registered(game.id)
        if registered >= game.max_slots:
            return
        next_p.status = ParticipantStatus.REGISTERED.value
        game.occupied_slots = registered + 1
        if game.occupied_slots >= game.max_slots:
            game.status = GameStatus.FULL.value

    async def start_game(self, game: Game) -> Game:
        game.status = GameStatus.IN_PROGRESS.value
        game.started_at = datetime.now(ZoneInfo(self.settings.timezone))
        await self.session.flush()
        await self.logs.log("game_started", details=f"game_id={game.id}")
        return game

    async def finish_and_archive(self, game: Game) -> Game:
        game.status = GameStatus.ARCHIVED.value
        game.finished_at = datetime.now(ZoneInfo(self.settings.timezone))
        await self.session.flush()
        await self.logs.log("game_archived", details=f"game_id={game.id}")
        return game

    async def cancel_game(self, admin: User, game: Game) -> Game:
        game.status = GameStatus.CANCELLED.value
        await self.session.flush()
        await self.notifications.notifications.delete_for_game(game.id)
        await self.logs.log(
            "game_cancelled", admin.telegram_id, f"game_id={game.id}"
        )
        return game

    async def update_game(self, game: Game, **kwargs) -> Game:
        game = await self.games.update(game, **kwargs)
        if game.status in (GameStatus.OPEN.value, GameStatus.FULL.value):
            await self.notifications.schedule_for_game(game)
        return game

    async def publish_draft(self, game: Game) -> Game:
        game.status = GameStatus.OPEN.value
        await self.session.flush()
        await self.notifications.schedule_for_game(game)
        return game

    async def get_participant_status(self, game: Game, user: User) -> str | None:
        p = await self.games.get_participant(game.id, user.id)
        if not p or p.status == ParticipantStatus.CANCELLED.value:
            return None
        return p.status
