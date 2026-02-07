from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import get_db_session
from app.infrastructure.repositories.stock_repository import StockRepositoryImpl
from app.infrastructure.repositories.stock_daily_repository import StockDailyRepositoryImpl
from app.infrastructure.acl.tushare_service import TushareService
from app.application.stock.use_cases.sync_stocks import SyncStocksUseCase
from app.application.stock.use_cases.sync_daily_history import SyncDailyHistoryUseCase
from app.application.dtos import BaseResponse
from pydantic import BaseModel

router = APIRouter()

class SyncStockResponse(BaseModel):
    synced_count: int
    message: str

class SyncStockDailyResponse(BaseModel):
    synced_stocks: int
    total_rows: int
    message: str

@router.post(
    "/sync",
    response_model=BaseResponse[SyncStockResponse],
    status_code=status.HTTP_200_OK,
    summary="同步股票基础数据",
    description="从 Tushare 获取最新股票列表并更新到本地数据库"
)
async def sync_stocks(
    db: AsyncSession = Depends(get_db_session),
):
    """
    触发股票数据同步任务
    """
    # 依赖注入：Repository -> UseCase
    repo = StockRepositoryImpl(db)
    provider = TushareService()
    use_case = SyncStocksUseCase(repo, provider)
    
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
    db: AsyncSession = Depends(get_db_session),
):
    """
    触发股票日线数据同步任务
    """
    stock_repo = StockRepositoryImpl(db)
    daily_repo = StockDailyRepositoryImpl(db)
    provider = TushareService()
    
    use_case = SyncDailyHistoryUseCase(stock_repo, daily_repo, provider)
    
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
