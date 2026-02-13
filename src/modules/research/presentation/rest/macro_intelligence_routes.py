"""
宏观情报员 REST 接口。

提供按标的进行宏观情报分析的 HTTP 入口；响应体由代码塞入 input、macro_indicators、output（与其他专家对称）。
"""
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import BadRequestException
from src.shared.infrastructure.db.session import get_db_session
from src.modules.research.application.macro_intelligence_service import (
    MacroIntelligenceService,
)
from src.modules.research.container import ResearchContainer
from src.modules.research.domain.exceptions import LLMOutputParseError


router = APIRouter()


async def get_macro_intelligence_service(
    db: AsyncSession = Depends(get_db_session),
) -> MacroIntelligenceService:
    """
    通过 Research 模块 Composition Root 获取宏观情报员服务。
    
    装配 MacroDataAdapter（注入 GetStockBasicInfoUseCase + WebSearchService）、
    MacroContextBuilderImpl、MacroIntelligenceAgentAdapter（注入 LLMAdapter），
    组装 MacroIntelligenceService。
    
    Args:
        db: 数据库会话（通过 FastAPI Depends 注入）
        
    Returns:
        MacroIntelligenceService: 装配好的宏观情报员服务实例
    """
    return ResearchContainer(db).macro_intelligence_service()


# ---------- 响应模型 ----------
class MacroIntelligenceApiResponse(BaseModel):
    """
    宏观情报接口响应：解析结果 + input、macro_indicators、output。
    
    与技术分析师（technical_indicators）、财务审计员（financial_indicators）、
    估值建模师（valuation_indicators）结构对称。
    """

    macro_environment: Literal["Favorable (有利)", "Neutral (中性)", "Unfavorable (不利)"] = Field(
        ..., description="宏观环境综合判定（三值之一）"
    )
    confidence_score: float = Field(..., description="置信度评分（0.0-1.0）")
    macro_summary: str = Field(..., description="宏观环境综合判断")
    dimension_analyses: list[dict[str, Any]] = Field(
        ..., description="四个维度的详细分析（货币、政策、经济、行业）"
    )
    key_opportunities: list[str] = Field(..., description="宏观层面的机会列表")
    key_risks: list[str] = Field(..., description="宏观层面的风险列表")
    information_sources: list[str] = Field(..., description="引用的信息来源 URL 列表")
    input: str = Field(..., description="送入大模型的 user prompt")
    macro_indicators: dict[str, Any] = Field(
        ..., description="宏观上下文快照（用于填充 prompt，与其他专家的 indicators 对应）"
    )
    output: str = Field(..., description="大模型原始返回字符串")


# ---------- 接口 ----------
@router.get(
    "/macro-intelligence",
    response_model=MacroIntelligenceApiResponse,
    summary="对指定股票进行宏观情报分析",
    description=(
        "基于股票所属行业，通过 Web 搜索获取四维度宏观情报（货币政策、产业政策、宏观经济、行业景气），"
        "调用大模型生成证据驱动的宏观环境评估。响应体含 input、macro_indicators、output（代码塞入，与其他专家接口一致）。"
    ),
)
async def run_macro_intelligence(
    symbol: str = Query(..., description="股票代码，如 000001.SZ"),
    service: MacroIntelligenceService = Depends(get_macro_intelligence_service),
) -> MacroIntelligenceApiResponse:
    """
    对单个标的运行宏观情报分析。
    
    响应体包含解析结果及 input、macro_indicators、output（由代码填入）。
    
    Args:
        symbol: 股票代码（Query 参数）
        service: 宏观情报员服务实例（通过依赖注入获取）
        
    Returns:
        MacroIntelligenceApiResponse: 宏观分析结果
        
    Raises:
        HTTPException 400: symbol 缺失、标的不存在、或宏观搜索全部失败
        HTTPException 422: LLM 返回内容无法解析
        HTTPException 500: 其他未预期异常
    """
    try:
        result = await service.run(symbol=symbol.strip())
        return MacroIntelligenceApiResponse(**result)
    except BadRequestException as e:
        logger.warning("宏观情报分析请求错误: {}", e.message)
        raise HTTPException(status_code=400, detail=e.message)
    except LLMOutputParseError as e:
        logger.warning("宏观情报 LLM 解析失败: {}", e.message)
        raise HTTPException(status_code=422, detail=e.message)
    except Exception as e:
        logger.exception("宏观情报分析执行异常: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e))
