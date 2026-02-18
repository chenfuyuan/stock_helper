# Standard library imports
import asyncio
from typing import Optional

# Third-party imports
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# Application imports
from src.modules.data_engineering.application.commands.sync_daily_history_cmd import (
    SyncDailyHistoryCmd,
)
from src.modules.data_engineering.application.commands.sync_stock_list_cmd import (
    SyncStockListCmd,
)
from src.modules.data_engineering.application.commands.sync_incremental_finance_cmd import (
    SyncIncrementalFinanceCmd,
)

# Domain ports
from src.modules.data_engineering.domain.ports.providers.market_quote_provider import (
    IMarketQuoteProvider,
)
from src.modules.data_engineering.domain.ports.providers.stock_basic_provider import (
    IStockBasicProvider,
)
from src.modules.data_engineering.domain.ports.providers.financial_data_provider import (
    IFinancialDataProvider,
)
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import (
    IFinancialDataRepository,
)
from src.modules.data_engineering.domain.ports.repositories.sync_task_repo import (
    ISyncTaskRepository,
)

# Infrastructure
from src.modules.data_engineering.infrastructure.external_apis.tushare.client import (
    TushareClient,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import (
    StockDailyRepositoryImpl,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import (
    StockRepositoryImpl,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_finance_repo import (
    StockFinanceRepositoryImpl,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_sync_task_repo import (
    SyncTaskRepositoryImpl,
)

# Shared
from src.shared.dtos import BaseResponse
from src.shared.infrastructure.db.session import get_db_session

# Response Models
class SyncStockResponse(BaseModel):
    """股票同步响应模型。"""
    synced_count: int
    message: str


class SyncStockDailyResponse(BaseModel):
    """股票日线同步响应模型。"""
    synced_stocks: int
    total_rows: int
    message: str


class SyncFinanceIncrementalResponse(BaseModel):
    """财务增量同步响应模型。"""
    status: str
    synced_count: int
    failed_count: int
    retry_count: int
    retry_success_count: int
    target_period: str
    message: str


class HistorySyncResponse(BaseModel):
    """历史全量同步响应模型。"""
    task_id: str
    status: str
    total_processed: int
    message: str


# Router
router = APIRouter()


# Dependency Injection Functions
async def get_stock_repo(
    db: AsyncSession = Depends(get_db_session),
) -> IStockBasicRepository:
    return StockRepositoryImpl(db)


async def get_daily_repo(
    db: AsyncSession = Depends(get_db_session),
) -> IMarketQuoteRepository:
    return StockDailyRepositoryImpl(db)


async def get_provider() -> TushareClient:
    return TushareClient()


async def get_sync_stocks_use_case(
    repo: IStockBasicRepository = Depends(get_stock_repo),
    provider: IStockBasicProvider = Depends(get_provider),
) -> SyncStockListCmd:
    return SyncStockListCmd(repo, provider)


async def get_sync_daily_use_case(
    stock_repo: IStockBasicRepository = Depends(get_stock_repo),
    daily_repo: IMarketQuoteRepository = Depends(get_daily_repo),
    provider: IMarketQuoteProvider = Depends(get_provider),
) -> SyncDailyHistoryCmd:
    return SyncDailyHistoryCmd(stock_repo, daily_repo, provider)


async def get_finance_repo(
    db: AsyncSession = Depends(get_db_session),
) -> IFinancialDataRepository:
    return StockFinanceRepositoryImpl(db)


async def get_sync_task_repo(
    db: AsyncSession = Depends(get_db_session),
) -> ISyncTaskRepository:
    return SyncTaskRepositoryImpl(db)


async def get_finance_provider() -> TushareClient:
    return TushareClient()


async def get_sync_finance_incremental_use_case(
    finance_repo: IFinancialDataRepository = Depends(get_finance_repo),
    stock_repo: IStockBasicRepository = Depends(get_stock_repo),
    sync_task_repo: ISyncTaskRepository = Depends(get_sync_task_repo),
    data_provider: IFinancialDataProvider = Depends(get_finance_provider),
) -> SyncIncrementalFinanceCmd:
    return SyncIncrementalFinanceCmd(finance_repo, stock_repo, sync_task_repo, data_provider)


# API Routes
@router.post("/sync", response_model=BaseResponse[SyncStockResponse])
async def sync_stocks(
    use_case: SyncStockListCmd = Depends(get_sync_stocks_use_case),
):
    """
    同步股票基础列表
    """
    logger.info("收到股票列表同步请求")
    try:
        result = await use_case.execute()
        logger.info(f"股票列表同步完成：{result.synced_count} 只股票")
        return BaseResponse(
            success=True,
            code="SYNC_SUCCESS",
            message="Stock sync success",
            data=SyncStockResponse(synced_count=result.synced_count, message=result.message),
        )
    except Exception as e:
        logger.exception(f"股票同步失败：{str(e)}")
        raise e


@router.post("/sync/daily/incremental", response_model=BaseResponse[SyncStockDailyResponse])
async def sync_stock_daily_incremental(
    limit: int = 10,
    offset: int = 0,
    symbol: str | None = None,
    use_case: SyncDailyHistoryCmd = Depends(get_sync_daily_use_case),
):
    """
    增量同步股票日线历史数据（日常操作）
    
    用于定期同步最新数据，支持分页处理避免超时。
    可指定股票代码同步单只股票，不指定则按分页同步多只股票。
    """
    logger.info(f"收到日线增量同步请求：limit={limit}, offset={offset}, symbol={symbol}")
    try:
        result = await use_case.execute(limit=limit, offset=offset, symbol=symbol)
        logger.info(
            f"日线增量同步完成：{result.synced_stocks} 只股票，"
            f"{result.total_rows} 条记录"
        )

        return BaseResponse(
            success=True,
            code="SYNC_DAILY_INCREMENTAL_SUCCESS",
            message="股票日线增量同步成功",
            data=SyncStockDailyResponse(
                synced_stocks=result.synced_stocks,
                total_rows=result.total_rows,
                message=result.message,
            ),
        )
    except Exception as e:
        logger.exception(f"日线增量同步失败：{str(e)}")
        raise e


@router.post("/sync/finance/incremental", response_model=BaseResponse[SyncFinanceIncrementalResponse])
async def sync_finance_incremental(
    actual_date: Optional[str] = None,
    use_case: SyncIncrementalFinanceCmd = Depends(get_sync_finance_incremental_use_case),
):
    """
    财务数据增量同步（日常操作）
    
    用于定期同步最新披露的财务数据，支持多策略同步：
    - 策略 A：今日披露名单驱动（高优先级）
    - 策略 B：长尾轮询补齐缺失数据（低优先级）
    - 策略 C：失败重试机制（前置步骤）
    
    Args:
        actual_date: 可选，指定同步日期 (YYYYMMDD)，默认为当天
    
    Returns:
        包含同步结果详情的响应，包括成功/失败数量、重试统计等
    """
    logger.info(f"收到财务增量同步请求：actual_date={actual_date}")
    try:
        result = await use_case.execute(actual_date=actual_date)
        logger.info(
            f"财务增量同步完成：成功 {result.synced_count} 只，"
            f"失败 {result.failed_count} 只，目标期间 {result.target_period}"
        )

        return BaseResponse(
            success=True,
            code="FINANCE_INCREMENTAL_SYNC_SUCCESS",
            message="财务数据增量同步成功",
            data=SyncFinanceIncrementalResponse(
                status=result.status,
                synced_count=result.synced_count,
                failed_count=result.failed_count,
                retry_count=result.retry_count,
                retry_success_count=result.retry_success_count,
                target_period=result.target_period,
                message=result.message,
            ),
        )
    except Exception as e:
        logger.exception(f"财务增量同步失败：{str(e)}")
        raise e


@router.post("/sync/daily/full", response_model=BaseResponse[HistorySyncResponse])
async def sync_daily_history_full():
    """
    日线历史全量同步（管理操作）
    
    用于初始化或数据修复，一次性同步所有历史数据
    使用 SyncEngine 自动分批处理，适合低频手动触发
    
    异步运行：立即返回任务ID，任务在后台执行
    """
    from src.modules.data_engineering.application.services.daily_sync_service import (
        DailySyncService,
    )
    
    logger.info("收到日线历史全量同步请求")
    try:
        service = DailySyncService()
        
        # 创建后台任务，不等待完成
        task = asyncio.create_task(service.run_history_sync())
        
        # 立即返回响应，包含任务引用信息
        return BaseResponse(
            success=True,
            code="DAILY_HISTORY_FULL_SYNC_STARTED",
            message="日线历史全量同步已启动（后台运行）",
            data=HistorySyncResponse(
                task_id=f"background_task_{id(task)}",
                status="running",
                total_processed=0,
                message="任务正在后台执行，请通过其他接口查询执行状态",
            ),
        )
    except Exception as e:
        logger.exception(f"启动日线历史全量同步失败：{str(e)}")
        raise e


@router.post("/sync/finance/full", response_model=BaseResponse[HistorySyncResponse])
async def sync_finance_history_full():
    """
    财务历史全量同步（管理操作）
    
    用于初始化或数据修复，一次性同步所有财务历史数据
    使用 SyncEngine 自动分批处理，适合低频手动触发
    
    异步运行：立即返回任务ID，任务在后台执行
    """
    from src.modules.data_engineering.application.services.finance_sync_service import (
        FinanceSyncService,
    )
    
    logger.info("收到财务历史全量同步请求")
    try:
        service = FinanceSyncService()
        
        # 创建后台任务，不等待完成
        task = asyncio.create_task(service.run_history_sync())
        
        # 立即返回响应，包含任务引用信息
        return BaseResponse(
            success=True,
            code="FINANCE_HISTORY_FULL_SYNC_STARTED",
            message="财务历史全量同步已启动（后台运行）",
            data=HistorySyncResponse(
                task_id=f"background_task_{id(task)}",
                status="running",
                total_processed=0,
                message="任务正在后台执行，请通过其他接口查询执行状态",
            ),
        )
    except Exception as e:
        logger.exception(f"启动财务历史全量同步失败：{str(e)}")
        raise e
