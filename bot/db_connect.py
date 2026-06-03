"""Параметры подключения asyncpg для бота (не для Alembic)."""
import ssl


def asyncpg_connect_args(database_url: str) -> dict:
    """
    Railway proxy (*.rlwy.net): SSL без проверки сертификата прокси.
    create_default_context() часто даёт Connection reset by peer на Railway.
    """
    args: dict = {"timeout": 60, "command_timeout": 60}
    if "rlwy.net" in database_url or "railway.app" in database_url:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        args["ssl"] = ctx
    return args
