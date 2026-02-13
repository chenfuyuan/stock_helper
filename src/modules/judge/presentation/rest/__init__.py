"""Judge REST 接口：统一导出 router，prefix=/judge。"""
from fastapi import APIRouter

from . import judge_router

router = APIRouter(prefix="/judge", tags=["judge"])
router.include_router(judge_router.router)  # path: /verdict -> /judge/verdict
