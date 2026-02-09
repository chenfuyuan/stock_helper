from fastapi import APIRouter
from src.api import health
from src.modules.data_engineering.presentation.rest import stock_routes, scheduler_routes

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stock_routes.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(scheduler_routes.router, prefix="/scheduler", tags=["scheduler"])
