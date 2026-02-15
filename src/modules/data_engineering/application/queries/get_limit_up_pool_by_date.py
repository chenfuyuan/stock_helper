from datetime import date

from src.modules.data_engineering.domain.model.limit_up_pool import LimitUpPoolStock
from src.modules.data_engineering.domain.ports.repositories.limit_up_pool_repo import (
    ILimitUpPoolRepository,
)
from src.shared.application.use_cases import BaseUseCase


class GetLimitUpPoolByDateUseCase(BaseUseCase):
    """
    按日期查询涨停池数据用例
    """

    def __init__(self, limit_up_pool_repo: ILimitUpPoolRepository):
        self.limit_up_pool_repo = limit_up_pool_repo

    async def execute(self, trade_date: date) -> list[LimitUpPoolStock]:
        """
        查询指定日期的涨停池记录
        
        Args:
            trade_date: 交易日期
            
        Returns:
            list[LimitUpPoolStock]: 涨停池记录列表
        """
        return await self.limit_up_pool_repo.get_by_date(trade_date)
