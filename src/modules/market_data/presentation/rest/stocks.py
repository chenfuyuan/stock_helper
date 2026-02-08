from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.infrastructure.db.session import get_db_session
from src.modules.market_data.infrastructure.adapters.persistence.repositories.stock_repository import StockRepositoryImpl
from src.modules.market_data.infrastructure.adapters.persistence.repositories.stock_daily_repository import StockDailyRepositoryImpl
from src.modules.market_data.infrastructure.adapters.tushare.tushare_api import TushareService
from src.modules.market_data.domain.repositories import StockRepository, StockDailyRepository
from src.modules.market_data.domain.services import StockDataProvider
from src.modules.market_data.application.use_cases.sync_stocks import SyncStocksUseCase
from src.modules.market_data.application.use_cases.sync_daily_history import SyncDailyHistoryUseCase
from src.shared.dtos import BaseResponse
from pydantic import BaseModel

router = APIRouter()

class SyncStockResponse(BaseModel):
    synced_count: int
    message: str

class SyncStockDailyResponse(BaseModel):
    synced_stocks: int
    total_rows: int
    message: str

# --- Dependency Injection Functions ---
async def get_stock_repo(db: AsyncSession = Depends(get_db_session)) -> StockRepository:
    return StockRepositoryImpl(db)

async def get_daily_repo(db: AsyncSession = Depends(get_db_session)) -> StockDailyRepository:
    return StockDailyRepositoryImpl(db)

async def get_data_provider() -> StockDataProvider:
    # 这里可以在未来根据配置返回不同的 Provider
    return TushareService()

async def get_sync_stocks_use_case(
    repo: StockRepository = Depends(get_stock_repo),
    provider: StockDataProvider = Depends(get_data_provider)
) -> SyncStocksUseCase:
    return SyncStocksUseCase(repo, provider)

async def get_sync_daily_use_case(
    stock_repo: StockRepository = Depends(get_stock_repo),
    daily_repo: StockDailyRepository = Depends(get_daily_repo),
    provider: StockDataProvider = Depends(get_data_provider)
) -> SyncDailyHistoryUseCase:
    return SyncDailyHistoryUseCase(stock_repo, daily_repo, provider)

# --- Routes ---

@router.post(
    "/sync",
    response_model=BaseResponse[SyncStockResponse],
    status_code=status.HTTP_200_OK,
    summary="同步股票基础数据",
    description="从 Tushare 获取最新股票列表并更新到本地数据库"
)
async def sync_stocks(
    use_case: SyncStocksUseCase = Depends(get_sync_stocks_use_case),
):
    """
    触发股票数据同步任务
    """
    # 执行业务逻辑
    result = await use_case.execute()
    
    return BaseResponse(
        success=True,
        code="SYNC_SUCCESS",
        message="股票数据同步成功",
        data=SyncStockResponse(
            synced_count=result.synced_count,
            message=result.message
        )
    )

@router.post(
    "/sync/daily",
    response_model=BaseResponse[SyncStockDailyResponse],
    status_code=status.HTTP_200_OK,
    summary="同步股票日线历史数据",
    description="分批获取所有股票的历史日线数据"
)
async def sync_stock_daily(
    limit: int = 10,
    offset: int = 0,
    use_case: SyncDailyHistoryUseCase = Depends(get_sync_daily_use_case),
):
    """
    触发股票日线数据同步任务
    """
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
