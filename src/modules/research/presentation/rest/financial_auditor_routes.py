"""
财务审计员 REST 接口。
提供按标的进行财务审计的 HTTP 入口；响应体由代码塞入 input、financial_indicators、output（与技术分析师 technical_indicators 对应）。
"""
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import BadRequestException
from src.shared.infrastructure.db.session import get_db_session
from src.modules.research.application.financial_auditor_service import (
    FinancialAuditorService,
)
from src.modules.research.container import ResearchContainer
from src.modules.research.domain.exceptions import LLMOutputParseError


router = APIRouter()


async def get_financial_auditor_service(
    db: AsyncSession = Depends(get_db_session),
) -> FinancialAuditorService:
    """通过 Research 模块 Composition Root 获取财务审计员服务，不直接依赖 data_engineering.infrastructure。"""
    return ResearchContainer(db).financial_auditor_service()


# ---------- 响应模型 ----------
class FinancialAuditApiResponse(BaseModel):
    """财务审计接口响应：解析结果 + input、financial_indicators、output（与技术分析师一致）。"""

    financial_score: int
    signal: Literal[
        "STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG_BEARISH"
    ]
    confidence: float
    summary_reasoning: str
    dimension_analyses: list[dict[str, Any]] = Field(
        ..., description="5D 维度分析结果"
    )
    key_risks: list[str] = Field(..., description="主要风险标记")
    risk_warning: str
    input: str = Field(..., description="送入大模型的 user prompt")
    financial_indicators: dict[str, Any] = Field(
        ..., description="财务指标快照（用于填充 prompt，与技术分析师 technical_indicators 对应）"
    )
    output: str = Field(..., description="大模型原始返回字符串")


# ---------- 接口 ----------
@router.get(
    "/financial-audit",
    response_model=FinancialAuditApiResponse,
    summary="对指定股票进行财务审计",
    description="根据财务指标数据构建快照，并调用大模型生成证据驱动的 5D 财务审计观点。响应体含 input、financial_indicators、output（代码塞入，与技术分析师接口一致）。",
)
async def run_financial_audit(
    symbol: str = Query(..., description="股票代码，如 000001.SZ"),
    limit: int = Query(5, ge=1, le=20, description="取最近几期财务数据，默认 5 期"),
    service: FinancialAuditorService = Depends(get_financial_auditor_service),
) -> FinancialAuditApiResponse:
    """
    对单个标的运行财务审计；响应体包含解析结果及 input、financial_indicators、output（由代码填入）。
    """
    try:
        result = await service.run(symbol=symbol.strip(), limit=limit)
        return FinancialAuditApiResponse(**result)
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except LLMOutputParseError as e:
        logger.warning("财务审计 LLM 解析失败: {}", e.message)
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.exception("财务审计执行异常: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))
