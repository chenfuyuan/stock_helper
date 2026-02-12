# 数据工程模块 REST 接口：对外暴露统一 router，合并股票与调度子路由。
from fastapi import APIRouter

from . import stock_routes, scheduler_routes

router = APIRouter()
router.include_router(stock_routes.router, prefix="/stocks", tags=["stocks"])
router.include_router(scheduler_routes.router, prefix="/scheduler", tags=["scheduler"])
