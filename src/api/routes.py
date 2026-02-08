from fastapi import APIRouter
from src.api import health
from src.modules.market_data.presentation.rest import stocks, scheduler

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
