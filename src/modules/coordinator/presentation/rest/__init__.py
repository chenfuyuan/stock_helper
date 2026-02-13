"""
Coordinator REST 接口：统一导出 router，prefix=/coordinator。
"""
from fastapi import APIRouter

from . import research_routes
from . import session_routes

router = APIRouter(prefix="/coordinator", tags=["Coordinator"])
router.include_router(research_routes.router)
router.include_router(session_routes.router)
