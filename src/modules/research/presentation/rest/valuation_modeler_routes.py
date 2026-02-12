"""
估值建模师 REST 接口。
提供按标的进行估值建模的 HTTP 入口；响应体由代码塞入 input、valuation_indicators、output。
"""
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import BadRequestException
from src.shared.infrastructure.db.session import get_db_session
from src.modules.research.application.valuation_modeler_service import (
    ValuationModelerService,
)
from src.modules.research.container import ResearchContainer
from src.modules.research.domain.exceptions import LLMOutputParseError


router = APIRouter()


async def get_valuation_modeler_service(
    db: AsyncSession = Depends(get_db_session),
) -> ValuationModelerService:
    """通过 Research 模块 Composition Root 获取估值建模师服务，不直接依赖 data_engineering.infrastructure。"""
    return ResearchContainer(db).valuation_modeler_service()


# ---------- 响应模型 ----------
class IntrinsicValueRangeResponse(BaseModel):
    """内在价值区间响应。"""

    lower_bound: str = Field(..., description="保守模型推导的价格下界（含推导依据）")
    upper_bound: str = Field(..., description="乐观模型推导的价格上界（含推导依据）")


class ValuationModelApiResponse(BaseModel):
    """估值建模接口响应：解析结果 + input、valuation_indicators、output。"""

    valuation_verdict: Literal["Undervalued (低估)", "Fair (合理)", "Overvalued (高估)"]
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度 0~1")
    estimated_intrinsic_value_range: IntrinsicValueRangeResponse
    key_evidence: list[str] = Field(..., min_length=1, description="证据列表")
    risk_factors: list[str] = Field(..., min_length=1, description="风险列表")
    reasoning_summary: str = Field(..., description="专业精炼总结")
    input: str = Field(..., description="送入大模型的 user prompt")
    valuation_indicators: dict[str, Any] = Field(
        ..., description="估值指标快照（用于填充 prompt）"
    )
    output: str = Field(..., description="大模型原始返回字符串")


# ---------- 接口 ----------
@router.get(
    "/valuation-model",
    response_model=ValuationModelApiResponse,
    summary="对指定股票进行估值建模",
    description='基于基本面数据计算标的的"内在价值"与"安全边际"，剥离市场情绪，仅基于估值模型和财务指标进行判断。响应体含 input、valuation_indicators、output（代码塞入）。',
)
async def run_valuation_model(
    symbol: str = Query(..., description="股票代码，如 000001.SZ"),
    service: ValuationModelerService = Depends(get_valuation_modeler_service),
) -> ValuationModelApiResponse:
    """
    对单个标的运行估值建模；响应体包含解析结果及 input、valuation_indicators、output（由代码填入）。
    """
    try:
        result = await service.run(symbol=symbol.strip())
        return ValuationModelApiResponse(**result)
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except LLMOutputParseError as e:
        logger.warning("估值建模 LLM 解析失败: {}", e.message)
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.exception("估值建模执行异常: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))
