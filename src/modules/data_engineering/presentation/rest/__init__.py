# 数据工程模块 REST 接口：对外暴露统一 router
from fastapi import APIRouter

from . import market_router, stock_routes

router = APIRouter()
router.include_router(stock_routes.router, prefix="/stocks", tags=["stocks"])
router.include_router(market_router.router, prefix="/market", tags=["market"])
