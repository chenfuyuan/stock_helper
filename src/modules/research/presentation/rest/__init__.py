# Research 模块 REST 接口：对外暴露统一 router，合并技术分析、财务审计、估值建模、宏观情报子路由。
from fastapi import APIRouter

from . import (
    catalyst_detective_routes,
    financial_auditor_routes,
    macro_intelligence_routes,
    technical_analyst_routes,
    valuation_modeler_routes,
)

router = APIRouter(prefix="/research", tags=["Research"])
router.include_router(technical_analyst_routes.router)
router.include_router(financial_auditor_routes.router)
router.include_router(valuation_modeler_routes.router)
router.include_router(macro_intelligence_routes.router)
router.include_router(catalyst_detective_routes.router)
