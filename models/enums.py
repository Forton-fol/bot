import enum


class RoleName(str, enum.Enum):
    PLAYER = "player"
    MASTER = "master"
    ADMIN = "admin"


class GameStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    FULL = "FULL"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    ARCHIVED = "ARCHIVED"
    CANCELLED = "CANCELLED"


class ParticipantStatus(str, enum.Enum):
    REGISTERED = "registered"
    WAITLIST = "waitlist"
    CANCELLED = "cancelled"


class NotificationType(str, enum.Enum):
    REMINDER_1_DAY = "reminder_1_day"
    REMINDER_12_HOURS = "reminder_12_hours"
    REMINDER_1_HOUR = "reminder_1_hour"
    GAME_START = "game_start"
