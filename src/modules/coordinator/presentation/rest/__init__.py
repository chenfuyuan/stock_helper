"""
Coordinator REST 接口：统一导出 router，prefix=/coordinator。
"""
from fastapi import APIRouter

from . import research_routes

router = APIRouter(prefix="/coordinator", tags=["Coordinator"])
router.include_router(research_routes.router)
