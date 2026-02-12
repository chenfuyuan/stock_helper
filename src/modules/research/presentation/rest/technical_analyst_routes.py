"""
技术分析师 REST 接口。
提供按标的与日期进行技术分析的 HTTP 入口；响应体由代码塞入 input、technical_indicators、output。
"""
from datetime import date
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.db.session import get_db_session
from src.modules.research.application.technical_analyst_service import TechnicalAnalystService
from src.modules.research.container import ResearchContainer
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import BadRequestException


router = APIRouter()


async def get_technical_analyst_service(
    db: AsyncSession = Depends(get_db_session),
) -> TechnicalAnalystService:
    """通过 Research 模块 Composition Root 获取技术分析师服务，不直接依赖 data_engineering.infrastructure。"""
    return ResearchContainer(db).technical_analyst_service()


# ---------- 响应模型（input、technical_indicators、output 由代码塞入，非大模型拼接） ----------
class TechnicalAnalysisApiResponse(BaseModel):
    """技术分析接口响应：解析结果 + 大模型 input、technical_indicators、output。"""

    signal: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: float
    summary_reasoning: str
    key_technical_levels: dict[str, Any] = Field(..., description="支撑/阻力")
    risk_warning: str
    input: str = Field(..., description="送入大模型的 user prompt")
    technical_indicators: dict[str, Any] = Field(
        ...,
        description="技术指标快照（用于填充 prompt）",
    )
    output: str = Field(..., description="大模型原始返回字符串")


# ---------- 接口 ----------
@router.get(
    "/technical-analysis",
    response_model=TechnicalAnalysisApiResponse,
    summary="对指定股票进行技术分析",
    description="根据日线数据计算技术指标，并调用大模型生成证据驱动的技术面观点。响应体含 input、technical_indicators、output（代码塞入）。",
)
async def run_technical_analysis(
    ticker: str = Query(..., description="股票代码，如 000001.SZ"),
    analysis_date: Optional[str] = Query(
        None,
        description="分析基准日，YYYY-MM-DD；不传则使用当前日期",
    ),
    service: TechnicalAnalystService = Depends(get_technical_analyst_service),
) -> TechnicalAnalysisApiResponse:
    """
    对单个标的运行技术分析；响应体包含解析结果及 input、technical_indicators、output（由代码填入）。
    """
    try:
        date_obj = date.fromisoformat(analysis_date) if analysis_date else date.today()
        result = await service.run(ticker=ticker.strip(), analysis_date=date_obj)
        return TechnicalAnalysisApiResponse(**result)
    except BadRequestException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except LLMOutputParseError as e:
        logger.warning("技术分析 LLM 解析失败: {}", e.message)
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.exception("技术分析执行异常: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))
