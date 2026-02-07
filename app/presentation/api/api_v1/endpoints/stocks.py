from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import get_db_session
from app.infrastructure.repositories.stock_repository import StockRepositoryImpl
from app.application.stock.use_cases import SyncStocksUseCase
from app.application.dtos import BaseResponse
from pydantic import BaseModel

router = APIRouter()

class SyncStockResponse(BaseModel):
    synced_count: int
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
    use_case = SyncStocksUseCase(repo)
    
    # 执行业务逻辑
    result = await use_case.execute()
    
    return BaseResponse(
        success=True,
        code="SYNC_SUCCESS",
        message="股票数据同步成功",
        data=SyncStockResponse(
            synced_count=result["synced_count"],
            message=result["message"]
        )
    )
