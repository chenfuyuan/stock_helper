from fastapi import APIRouter

from app.presentation.api.api_v1.endpoints import health, stocks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
