import json
import logging
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.db.session import get_db_session
from src.modules.research.container import ResearchContainer
from src.modules.research.application.catalyst_detective_service import CatalystDetectiveService
from src.modules.research.domain.dtos.catalyst_dtos import (
    CatalystEvent,
    CatalystDimensionAnalysis,
)
from src.modules.research.domain.exceptions import LLMOutputParseError
from src.shared.domain.exceptions import BadRequestException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Research: Catalyst Detective"])


async def get_catalyst_detective_service(
    db: AsyncSession = Depends(get_db_session),
) -> CatalystDetectiveService:
    """
    通过 Research 模块 Composition Root 获取催化剂侦探服务
    """
    return ResearchContainer(db).catalyst_detective_service()


class CatalystDetectiveApiResponse(BaseModel):
    """
    催化剂侦探 API 响应模型
    包含分析结果与调试信息 (input/output/indicators)
    """
    stock_name: str
    symbol: str

    catalyst_assessment: Literal["Positive (正面催化)", "Neutral (中性)", "Negative (负面催化)"]
    confidence_score: float
    catalyst_summary: str
    dimension_analyses: List[CatalystDimensionAnalysis]
    positive_catalysts: List[CatalystEvent]
    negative_catalysts: List[CatalystEvent]
    information_sources: List[str]
    
    # Debug/Audit info
    input: str
    output: str
    catalyst_indicators: str  # The context used
    
@router.get("/catalyst-detective", response_model=CatalystDetectiveApiResponse)
async def get_catalyst_detective_analysis(
    symbol: str, 
    service: CatalystDetectiveService = Depends(get_catalyst_detective_service)
):
    try:
        result_dict = await service.run(symbol)
        dto = result_dict["result"]
        context = result_dict["catalyst_context"]
        indicators_json = json.dumps(context, ensure_ascii=False)

        return CatalystDetectiveApiResponse(
            stock_name=context["stock_name"],
            symbol=symbol,
            catalyst_assessment=dto["catalyst_assessment"],
            confidence_score=dto["confidence_score"],
            catalyst_summary=dto["catalyst_summary"],
            dimension_analyses=[CatalystDimensionAnalysis(**x) for x in dto["dimension_analyses"]],
            positive_catalysts=[CatalystEvent(**x) for x in dto["positive_catalysts"]],
            negative_catalysts=[CatalystEvent(**x) for x in dto["negative_catalysts"]],
            information_sources=dto["information_sources"],
            input=result_dict["user_prompt"],
            output=result_dict["raw_llm_output"],
            catalyst_indicators=indicators_json,
        )

    except BadRequestException as e:
        logger.warning("催化剂侦探请求错误：symbol=%s，错误=%s", symbol, e)
        raise HTTPException(status_code=400, detail=e.message)
    except LLMOutputParseError as e:
        logger.error(f"LLM parse error for {symbol}: {e}")
        raise HTTPException(status_code=422, detail="AI response parsing failed")
    except Exception as e:
        logger.exception(f"Unexpected error in catalyst detective for {symbol}")
        raise HTTPException(status_code=500, detail="Internal server error")
