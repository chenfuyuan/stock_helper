from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.application.commands.sync_daily_history_cmd import (
    SyncDailyHistoryCmd,
)

# Commands
from src.modules.data_engineering.application.commands.sync_stock_list_cmd import (
    SyncStockListCmd,
)
from src.modules.data_engineering.domain.ports.providers.market_quote_provider import (
    IMarketQuoteProvider,
)
from src.modules.data_engineering.domain.ports.providers.stock_basic_provider import (
    IStockBasicProvider,
)
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)

# Ports
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import (
    IStockBasicRepository,
)
from src.modules.data_engineering.infrastructure.external_apis.tushare.client import (
    TushareClient,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import (
    StockDailyRepositoryImpl,
)

# Infra
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import (
    StockRepositoryImpl,
)
from src.shared.dtos import BaseResponse
from src.shared.infrastructure.db.session import get_db_session

router = APIRouter()


class SyncStockResponse(BaseModel):
    synced_count: int
    message: str


class SyncStockDailyResponse(BaseModel):
    synced_stocks: int
    total_rows: int
    message: str


# Dependency Injection
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


@router.post("/sync/daily", response_model=BaseResponse[SyncStockDailyResponse])
async def sync_stock_daily(
    limit: int = 10,
    offset: int = 0,
    use_case: SyncDailyHistoryCmd = Depends(get_sync_daily_use_case),
):
    """
    同步股票日线历史数据
    """
    logger.info(f"收到日线历史同步请求：limit={limit}, offset={offset}")
    try:
        result = await use_case.execute(limit=limit, offset=offset)
        logger.info(
            f"日线历史同步完成：{result.synced_stocks} 只股票，"
            f"{result.total_rows} 条记录"
        )

        return BaseResponse(
            success=True,
            code="SYNC_DAILY_SUCCESS",
            message="股票日线数据同步成功",
            data=SyncStockDailyResponse(
                synced_stocks=result.synced_stocks,
                total_rows=result.total_rows,
                message=result.message,
            ),
        )
    except Exception as e:
        logger.exception(f"日线历史同步失败：{str(e)}")
        raise e


class HistorySyncResponse(BaseModel):
    """历史全量同步响应。"""
    task_id: str
    status: str
    total_processed: int
    message: str


@router.post("/sync/daily-history", response_model=BaseResponse[HistorySyncResponse])
async def sync_daily_history():
    """
    触发日线历史全量同步（一次性/低频操作，手动触发）。
    
    使用 SyncEngine 一次触发、自动分批、跑完全量。
    """
    from src.modules.data_engineering.application.services.data_sync_application_service import (
        DataSyncApplicationService,
    )
    
    logger.info("收到日线历史全量同步请求")
    try:
        service = DataSyncApplicationService()
        task = await service.run_daily_history_sync()
        
        logger.info(f"日线历史全量同步完成：task_id={task.id}, status={task.status.value}")
        
        return BaseResponse(
            success=True,
            code="DAILY_HISTORY_SYNC_SUCCESS",
            message="日线历史全量同步已启动",
            data=HistorySyncResponse(
                task_id=str(task.id),
                status=task.status.value,
                total_processed=task.total_processed,
                message=f"已处理 {task.total_processed} 条记录",
            ),
        )
    except Exception as e:
        logger.exception(f"日线历史全量同步失败：{str(e)}")
        raise e


@router.post("/sync/finance-history", response_model=BaseResponse[HistorySyncResponse])
async def sync_finance_history():
    """
    触发财务历史全量同步（一次性/低频操作，手动触发）。
    
    使用 SyncEngine 一次触发、自动分批、跑完全量。
    """
    from src.modules.data_engineering.application.services.data_sync_application_service import (
        DataSyncApplicationService,
    )
    
    logger.info("收到财务历史全量同步请求")
    try:
        service = DataSyncApplicationService()
        task = await service.run_finance_history_sync()
        
        logger.info(f"财务历史全量同步完成：task_id={task.id}, status={task.status.value}")
        
        return BaseResponse(
            success=True,
            code="FINANCE_HISTORY_SYNC_SUCCESS",
            message="财务历史全量同步已启动",
            data=HistorySyncResponse(
                task_id=str(task.id),
                status=task.status.value,
                total_processed=task.total_processed,
                message=f"已处理 {task.total_processed} 条记录",
            ),
        )
    except Exception as e:
        logger.exception(f"财务历史全量同步失败：{str(e)}")
        raise e
