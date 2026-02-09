from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from src.shared.infrastructure.db.session import get_db_session
from src.shared.dtos import BaseResponse

# Infra
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_stock_repo import StockRepositoryImpl
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_quote_repo import StockDailyRepositoryImpl
from src.modules.data_engineering.infrastructure.external_apis.tushare.client import TushareClient

# Ports
from src.modules.data_engineering.domain.ports.repositories.stock_basic_repo import IStockBasicRepository
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import IMarketQuoteRepository
from src.modules.data_engineering.domain.ports.providers.stock_basic_provider import IStockBasicProvider
from src.modules.data_engineering.domain.ports.providers.market_quote_provider import IMarketQuoteProvider

# Commands
from src.modules.data_engineering.application.commands.sync_stock_list_cmd import SyncStocksUseCase
from src.modules.data_engineering.application.commands.sync_daily_history import SyncDailyHistoryUseCase

router = APIRouter()

class SyncStockResponse(BaseModel):
    synced_count: int
    message: str

class SyncStockDailyResponse(BaseModel):
    synced_stocks: int
    total_rows: int
    message: str

# Dependency Injection
async def get_stock_repo(db: AsyncSession = Depends(get_db_session)) -> IStockBasicRepository:
    return StockRepositoryImpl(db)

async def get_daily_repo(db: AsyncSession = Depends(get_db_session)) -> IMarketQuoteRepository:
    return StockDailyRepositoryImpl(db)

async def get_provider() -> TushareClient:
    return TushareClient()

async def get_sync_stocks_use_case(
    repo: IStockBasicRepository = Depends(get_stock_repo),
    provider: IStockBasicProvider = Depends(get_provider)
) -> SyncStocksUseCase:
    return SyncStocksUseCase(repo, provider)

async def get_sync_daily_use_case(
    stock_repo: IStockBasicRepository = Depends(get_stock_repo),
    daily_repo: IMarketQuoteRepository = Depends(get_daily_repo),
    provider: IMarketQuoteProvider = Depends(get_provider)
) -> SyncDailyHistoryUseCase:
    return SyncDailyHistoryUseCase(stock_repo, daily_repo, provider)

@router.post("/sync", response_model=BaseResponse[SyncStockResponse])
async def sync_stocks(use_case: SyncStocksUseCase = Depends(get_sync_stocks_use_case)):
    result = await use_case.execute()
    # result is dict based on my previous edit
    return BaseResponse(
        success=True,
        code="SYNC_SUCCESS",
        message="Stock sync success",
        data=SyncStockResponse(
            synced_count=result["synced_count"],
            message=result["message"]
        )
    )

@router.post("/sync/daily", response_model=BaseResponse[SyncStockDailyResponse])
async def sync_stock_daily(
    limit: int = 10,
    offset: int = 0,
    use_case: SyncDailyHistoryUseCase = Depends(get_sync_daily_use_case),
):
    result = await use_case.execute(limit=limit, offset=offset)
    
    return BaseResponse(
        success=True,
        code="SYNC_DAILY_SUCCESS",
        message="股票日线数据同步成功",
        data=SyncStockDailyResponse(
            synced_stocks=result["synced_stocks"],
            total_rows=result["total_rows"],
            message=result["message"]
        )
    )
