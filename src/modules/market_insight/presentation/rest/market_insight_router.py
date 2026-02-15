"""
Market Insight REST 路由
提供概念热度查询、涨停股查询、每日复盘报告生成接口
"""

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.market_insight.application.dtos.market_insight_dtos import (
    ConceptHeatDTO,
    DailyReportResult,
    LimitUpStockDTO,
)
from src.modules.market_insight.container import MarketInsightContainer
from src.shared.infrastructure.db.session import get_async_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market-insight"])


async def get_container(
    session: AsyncSession = Depends(get_async_session),
) -> MarketInsightContainer:
    """依赖注入：获取 MarketInsightContainer"""
    return MarketInsightContainer(session)


@router.get(
    "/market-insight/concept-heat",
    response_model=List[ConceptHeatDTO],
    summary="查询概念热度",
    description="获取指定交易日的概念热度排名",
)
async def get_concept_heat(
    trade_date: date = Query(..., description="交易日期"),
    top_n: Optional[int] = Query(10, description="返回前 N 名概念"),
    container: MarketInsightContainer = Depends(get_container),
) -> List[ConceptHeatDTO]:
    """GET /api/market-insight/concept-heat：查询概念热度"""
    try:
        query = container.get_concept_heat_query()
        result = await query.execute(trade_date, top_n)
        return result
    except Exception as e:
        logger.exception(f"查询概念热度失败: {e}")
        raise HTTPException(status_code=500, detail="查询概念热度失败")


@router.get(
    "/market-insight/limit-up",
    response_model=List[LimitUpStockDTO],
    summary="查询涨停股",
    description="获取指定交易日的涨停股列表，支持按概念过滤",
)
async def get_limit_up(
    trade_date: date = Query(..., description="交易日期"),
    concept_code: Optional[str] = Query(None, description="概念代码（可选，用于过滤）"),
    container: MarketInsightContainer = Depends(get_container),
) -> List[LimitUpStockDTO]:
    """GET /api/market-insight/limit-up：查询涨停股"""
    try:
        query = container.get_limit_up_query()
        result = await query.execute(trade_date, concept_code)
        return result
    except Exception as e:
        logger.exception(f"查询涨停股失败: {e}")
        raise HTTPException(status_code=500, detail="查询涨停股失败")


@router.post(
    "/market-insight/daily-report",
    response_model=DailyReportResult,
    summary="生成每日复盘报告",
    description="触发指定日期的每日复盘计算，生成 Markdown 报告",
)
async def post_daily_report(
    trade_date: date = Query(..., description="交易日期"),
    container: MarketInsightContainer = Depends(get_container),
) -> DailyReportResult:
    """POST /api/market-insight/daily-report：生成每日复盘报告"""
    try:
        cmd = container.get_generate_daily_report_cmd()
        result = await cmd.execute(trade_date)
        return result
    except Exception as e:
        logger.exception(f"生成每日复盘报告失败: {e}")
        raise HTTPException(status_code=500, detail="生成每日复盘报告失败")
