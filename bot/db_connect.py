"""Общие параметры подключения asyncpg (бот + Alembic)."""
import ssl


def asyncpg_connect_args(database_url: str) -> dict:
    """
    Railway *.rlwy.net требует SSL через connect_args.
    Параметр ?ssl=require в URL asyncpg часто не понимает — отсюда таймауты.
    """
    args: dict = {"timeout": 60}
    if "rlwy.net" in database_url or "railway.app" in database_url:
        args["ssl"] = ssl.create_default_context()
    return args
