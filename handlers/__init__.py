from aiogram import Router

from handlers.admin import router as admin_router
from handlers.common import router as common_router
from handlers.master import router as master_router
from handlers.player import router as player_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(common_router)
    root.include_router(player_router)
    root.include_router(master_router)
    root.include_router(admin_router)
    return root
