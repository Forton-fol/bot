"""Параметры asyncpg для бота (не Alembic)."""
import ssl


def asyncpg_connect_args(database_url: str) -> dict:
    args: dict = {"timeout": 60, "command_timeout": 60}
    host = database_url

    # Внутренняя сеть Railway — SSL не нужен
    if "railway.internal" in host:
        return args

    if "rlwy.net" in host or "railway.app" in host:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        args["ssl"] = ctx

    return args
