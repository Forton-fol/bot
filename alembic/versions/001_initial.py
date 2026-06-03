"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("games_attended", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "action_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_logs_telegram_id", "action_logs", ["telegram_id"])

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("image_file_id", sa.String(length=512), nullable=True),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("game_time", sa.Time(), nullable=False),
        sa.Column("system_name", sa.String(length=128), nullable=False),
        sa.Column("session_type", sa.String(length=128), nullable=False),
        sa.Column("player_level", sa.String(length=128), nullable=False),
        sa.Column("character_level", sa.String(length=128), nullable=False),
        sa.Column("max_slots", sa.Integer(), nullable=False),
        sa.Column("occupied_slots", sa.Integer(), server_default="0", nullable=False),
        sa.Column("price", sa.String(length=64), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("room_text", sa.String(length=64), nullable=True),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False),
        sa.Column("master_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["master_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_games_game_date", "games", ["game_date"])
    op.create_index("ix_games_status", "games", ["status"])

    op.create_table(
        "game_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="registered", nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "user_id", name="uq_game_user"),
    )
    op.create_index("ix_game_participants_game_id", "game_participants", ["game_id"])
    op.create_index("ix_game_participants_user_id", "game_participants", ["user_id"])

    op.create_table(
        "points_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_points_history_user_id", "points_history", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_game_id", "notifications", ["game_id"])

    op.execute(
        "INSERT INTO roles (id, name) VALUES (1, 'player'), (2, 'master'), (3, 'admin')"
    )
    op.execute(
        "INSERT INTO rooms (id, name, address) VALUES "
        "(1, 'Кабинет 1', 'ул. Примерная, д. 1'), "
        "(2, 'Кабинет 2', 'ул. Примерная, д. 1')"
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("points_history")
    op.drop_table("game_participants")
    op.drop_table("games")
    op.drop_table("action_logs")
    op.drop_table("users")
    op.drop_table("rooms")
    op.drop_table("roles")
