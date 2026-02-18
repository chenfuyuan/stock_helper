"""
市场数据同步 REST API Router。

提供 AkShare 市场数据和概念数据的同步 HTTP 端点。
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.application.dtos.sync_result_dtos import (
    AkShareSyncResult,
    ConceptSyncResult,
)
from src.modules.data_engineering.container import DataEngineeringContainer
from src.shared.dtos import BaseResponse
from src.shared.infrastructure.db.session import get_db_session

router = APIRouter()


# 响应模型
class SingleSyncResponse(BaseModel):
    """单个数据同步响应模型。"""
    count: int
    message: str


# 依赖注入
async def get_container(
    session: AsyncSession = Depends(get_db_session),
) -> DataEngineeringContainer:
    """依赖注入：获取 DataEngineeringContainer 实例。"""
    return DataEngineeringContainer(session)


@router.post(
    "/sync",
    response_model=BaseResponse[AkShareSyncResult],
    summary="统一同步 AkShare 市场数据",
    description="同步5个市场数据：涨停池、炸板池、昨日涨停、龙虎榜、板块资金流向",
)
async def sync_akshare_market_data(
    trade_date: Optional[date] = Query(
        None,
        description="交易日期（YYYY-MM-DD），默认为当天",
    ),
    container: DataEngineeringContainer = Depends(get_container),
):
    """
    统一同步 AkShare 市场数据。
    
    Args:
        trade_date: 交易日期，默认为当天
        container: 依赖注入的 DataEngineeringContainer
        
    Returns:
        BaseResponse[AkShareSyncResult]: 同步结果
    """
    if trade_date is None:
        trade_date = date.today()
    
    logger.info(f"收到 AkShare 市场数据同步请求：{trade_date}")
    
    cmd = container.get_sync_akshare_market_data_cmd()
    result = await cmd.execute(trade_date)
    
    logger.info(
        f"AkShare 市场数据同步完成：{trade_date}，"
        f"涨停池 {result.limit_up_pool_count}，炸板池 {result.broken_board_count}，"
        f"昨日涨停 {result.previous_limit_up_count}，龙虎榜 {result.dragon_tiger_count}，"
        f"资金流向 {result.sector_capital_flow_count}，错误 {len(result.errors)}"
    )
    
    return BaseResponse(
        success=True,
        code="AKSHARE_SYNC_SUCCESS",
        message="AkShare 市场数据同步成功",
        data=result,
    )


@router.post(
    "/sync/limit-up-pool",
    response_model=BaseResponse[SingleSyncResponse],
    summary="同步涨停池数据",
    description="单独同步涨停池数据",
)
async def sync_limit_up_pool(
    trade_date: Optional[date] = Query(
        None,
        description="交易日期（YYYY-MM-DD），默认为当天",
    ),
    container: DataEngineeringContainer = Depends(get_container),
):
    """同步涨停池数据。"""
    if trade_date is None:
        trade_date = date.today()
    
    logger.info(f"收到涨停池同步请求：{trade_date}")
    
    cmd = container.get_sync_limit_up_pool_cmd()
    count = await cmd.execute(trade_date)
    
    message = f"涨停池同步完成：{count} 条"
    logger.info(message)
    
    return BaseResponse(
        success=True,
        code="LIMIT_UP_POOL_SYNC_SUCCESS",
        message=message,
        data=SingleSyncResponse(count=count, message=message),
    )


@router.post(
    "/sync/broken-board",
    response_model=BaseResponse[SingleSyncResponse],
    summary="同步炸板池数据",
    description="单独同步炸板池数据",
)
async def sync_broken_board(
    trade_date: Optional[date] = Query(
        None,
        description="交易日期（YYYY-MM-DD），默认为当天",
    ),
    container: DataEngineeringContainer = Depends(get_container),
):
    """同步炸板池数据。"""
    if trade_date is None:
        trade_date = date.today()
    
    logger.info(f"收到炸板池同步请求：{trade_date}")
    
    cmd = container.get_sync_broken_board_cmd()
    count = await cmd.execute(trade_date)
    
    message = f"炸板池同步完成：{count} 条"
    logger.info(message)
    
    return BaseResponse(
        success=True,
        code="BROKEN_BOARD_SYNC_SUCCESS",
        message=message,
        data=SingleSyncResponse(count=count, message=message),
    )


@router.post(
    "/sync/previous-limit-up",
    response_model=BaseResponse[SingleSyncResponse],
    summary="同步昨日涨停表现数据",
    description="单独同步昨日涨停表现数据",
)
async def sync_previous_limit_up(
    trade_date: Optional[date] = Query(
        None,
        description="交易日期（YYYY-MM-DD），默认为当天",
    ),
    container: DataEngineeringContainer = Depends(get_container),
):
    """同步昨日涨停表现数据。"""
    if trade_date is None:
        trade_date = date.today()
    
    logger.info(f"收到昨日涨停同步请求：{trade_date}")
    
    cmd = container.get_sync_previous_limit_up_cmd()
    count = await cmd.execute(trade_date)
    
    message = f"昨日涨停表现同步完成：{count} 条"
    logger.info(message)
    
    return BaseResponse(
        success=True,
        code="PREVIOUS_LIMIT_UP_SYNC_SUCCESS",
        message=message,
        data=SingleSyncResponse(count=count, message=message),
    )


@router.post(
    "/sync/dragon-tiger",
    response_model=BaseResponse[SingleSyncResponse],
    summary="同步龙虎榜数据",
    description="单独同步龙虎榜数据",
)
async def sync_dragon_tiger(
    trade_date: Optional[date] = Query(
        None,
        description="交易日期（YYYY-MM-DD），默认为当天",
    ),
    container: DataEngineeringContainer = Depends(get_container),
):
    """同步龙虎榜数据。"""
    if trade_date is None:
        trade_date = date.today()
    
    logger.info(f"收到龙虎榜同步请求：{trade_date}")
    
    cmd = container.get_sync_dragon_tiger_cmd()
    count = await cmd.execute(trade_date)
    
    message = f"龙虎榜同步完成：{count} 条"
    logger.info(message)
    
    return BaseResponse(
        success=True,
        code="DRAGON_TIGER_SYNC_SUCCESS",
        message=message,
        data=SingleSyncResponse(count=count, message=message),
    )


@router.post(
    "/sync/sector-capital-flow",
    response_model=BaseResponse[SingleSyncResponse],
    summary="同步板块资金流向数据",
    description="单独同步板块资金流向数据",
)
async def sync_sector_capital_flow(
    trade_date: Optional[date] = Query(
        None,
        description="交易日期（YYYY-MM-DD），默认为当天",
    ),
    container: DataEngineeringContainer = Depends(get_container),
):
    """同步板块资金流向数据。"""
    if trade_date is None:
        trade_date = date.today()
    
    logger.info(f"收到板块资金流向同步请求：{trade_date}")
    
    cmd = container.get_sync_sector_capital_flow_cmd()
    count = await cmd.execute(trade_date)
    
    message = f"板块资金流向同步完成：{count} 条"
    logger.info(message)
    
    return BaseResponse(
        success=True,
        code="SECTOR_CAPITAL_FLOW_SYNC_SUCCESS",
        message=message,
        data=SingleSyncResponse(count=count, message=message),
    )


@router.post(
    "/sync/concept",
    response_model=BaseResponse[ConceptSyncResult],
    summary="同步概念数据",
    description="同步概念板块及成份股数据",
)
async def sync_concept_data(
    container: DataEngineeringContainer = Depends(get_container),
):
    """同步概念数据。"""
    logger.info("收到概念数据同步请求")
    
    cmd = container.get_sync_concept_data_cmd()
    result = await cmd.execute()
    
    logger.info(
        f"概念数据同步完成：概念 {result.success_concepts}/{result.total_concepts}，"
        f"成份股映射 {result.total_stocks} 条，耗时 {result.elapsed_time:.2f}s"
    )
    
    return BaseResponse(
        success=True,
        code="CONCEPT_SYNC_SUCCESS",
        message="概念数据同步成功",
        data=result,
    )
