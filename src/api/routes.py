from fastapi import APIRouter

from src.api import health
from src.modules.data_engineering.presentation.rest import router as de_router
from src.modules.llm_platform.presentation.rest import router as llm_router
from src.modules.research.presentation.rest import router as research_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(de_router)
api_router.include_router(llm_router)
api_router.include_router(research_router)
