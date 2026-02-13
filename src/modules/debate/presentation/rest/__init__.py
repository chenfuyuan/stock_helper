"""Debate REST 接口：统一导出 router，prefix=/debate。"""
from fastapi import APIRouter

from . import debate_router

router = APIRouter(prefix="/debate", tags=["debate"])
router.include_router(debate_router.router)  # path: /run -> /debate/run
