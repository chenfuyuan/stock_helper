from fastapi import APIRouter
from src.api import health
from src.modules.data_engineering.presentation.rest import stock_routes, scheduler_routes
from src.modules.llm_platform.presentation.rest import config_routes, chat_routes
from src.modules.research.presentation.rest import technical_analyst_routes

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stock_routes.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(scheduler_routes.router, prefix="/scheduler", tags=["scheduler"])
api_router.include_router(config_routes.router)
api_router.include_router(chat_routes.router)
api_router.include_router(technical_analyst_routes.router)
