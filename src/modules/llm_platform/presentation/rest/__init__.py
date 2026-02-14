# LLM 平台模块 REST 接口：对外暴露统一 router，合并配置、聊天、搜索子路由。
from fastapi import APIRouter

from . import chat_routes, config_routes, search_routes

router = APIRouter()
router.include_router(config_routes.router)
router.include_router(chat_routes.router)
router.include_router(search_routes.router)
